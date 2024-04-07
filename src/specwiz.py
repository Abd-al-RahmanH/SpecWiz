__import__("pysqlite3")
import sys

sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import streamlit as st
from utils.upload_file import UploadFile
from utils.upload_data_manually import UploadDataManually
from utils.chatbot import ChatBot
import tempfile, os
from boxsdk import OAuth2, Client, object, CCGAuth
import os, time
from utils.load_config import LoadConfig
from langchain.vectorstores import Chroma
from utils.prepare_vectordb import PrepareVectorDB
from dotenv import load_dotenv

load_dotenv()

CONFIG = LoadConfig()

st.set_page_config(
    page_title="SpecWiz",
    page_icon="images/spec.png",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.image("images/specwiz.png", width=200)


# Define a function to remove the directory when a new session starts
def remove_directory_on_session_start():
    CONFIG.remove_directory(CONFIG.custom_persist_directory)


# Get a handle to the session state
session_state = st.session_state

# Check if the session state variable for session start exists
if "session_start" not in session_state:
    # If it doesn't exist, set it to True and remove the directory
    session_state.session_start = True
    remove_directory_on_session_start()


def get_box_files():
    auth = CCGAuth(
        client_id=os.getenv("BOX_CLIENT_ID"),
        client_secret=os.getenv("BOX_CLIENT_SECRET"),
        enterprise_id=os.getenv("BOX_ENTERPRISE_ID"),
    )
    client = Client(auth)

    folder_items = client.folder(folder_id=os.getenv("BOX_FOLDER_ID")).get_items()
    file_paths = []
    for item in folder_items:
        if isinstance(item, object.file.File):
            file_path = os.path.join(tempfile.mkdtemp(), item.name)
            with open(file_path, "wb") as f:
                item.download_to(f)
            file_paths.append(file_path)
    return file_paths


def main():
    genai_api_key_placeholder = st.empty()
    genai_api_key = genai_api_key_placeholder.text_input(
        "IBM WatsonX API Key", type="password"
    )
    if not genai_api_key:
        st.info("Please add your IBM WatsonX API key to continue.")
        st.stop()
    genai_api_key_placeholder.empty()

    # file_msg = ""
    with st.sidebar:

        st.image("images/specwiz.png", width=300)
        st.title("Welcome to SpecWiz!")

        st.markdown(
            "SpecWiz is an advanced platform built using IBM WatsonX."
            "It not only answers questions related to preprocessed ARB Technical Specifications, but also allows you to upload documents on the fly and chat with them."
            "It also summarizes documents."
            "Enter your IBM WatsonX API Key, and let SpecWiz hatch profound insights from documents, all powered by cutting-edge IBM WatsonX Gen AI"
        )

        rag_with_dropdown = st.selectbox(
            "Chat with",
            (
                "Preprocessed Doc",
                "Uploaded Doc",
                "Give Full Doc Summary",
            ),
        )
        if rag_with_dropdown == "Preprocessed Doc":
            if not len(os.listdir(CONFIG.persist_directory)) != 0:
                # with st.spinner("Getting files from Box"):
                preprocess_docs = get_box_files()
                st.toast(
                    "ADB documents fetched from Box. Please pre-process them by clicking 'Preprocess'"
                )
                time.sleep(5)
                if st.button("Preprocess"):
                    with st.spinner("Preprocessing ADB documents. Please wait..."):
                        doc_dir = []
                        for doc in preprocess_docs:
                            doc_dir.append(doc)
                        processed_file_msg = UploadDataManually.upload_data_manually(
                            doc_dir, genai_api_key
                        )
                        st.success(processed_file_msg)

        elif rag_with_dropdown == "Uploaded Doc":
            uploaded_docs = st.file_uploader("Upload files", accept_multiple_files=True)
            if st.button("Upload"):
                with st.spinner("Processing your ADB documents"):
                    doc_dir = []
                    for doc in uploaded_docs:
                        temp_dir = tempfile.mkdtemp()
                        path = os.path.join(temp_dir, doc.name)
                        with open(path, "wb") as f:
                            f.write(doc.getvalue())
                            doc_dir.append(path)
                file_msg = UploadFile.process_uploaded_files(
                    doc_dir, genai_api_key, rag_with_dropdown
                )
                st.success(file_msg)
        else:
            summarize_doc = st.file_uploader(
                "Summarize File", accept_multiple_files=True
            )

    # Store LLM generated responses
    if "messages" not in st.session_state.keys():
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello. I am SpecWiz - Your personalized architectural assistant! How may I assist you today?",
            }
        ]

    # display chat messages from history on app rerun
    for message in st.session_state.messages:

        with st.chat_message(message["role"], avatar="images/spec.png"):
            st.markdown(message["content"])

    if rag_with_dropdown == "Give Full Doc Summary":
        if st.sidebar.button("Summarize ADB Document"):
            prompt = "Please summarize my ADB document"
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user", avatar="images/user.png"):
                st.write(prompt)

            # if st.session_state.messages[-1]["role"] != "assistant":
            with st.chat_message("assistant", avatar="images/spec.png"):
                with st.spinner(
                    "Summarizing ADB document. This will not take long ...."
                ):
                    doc_dir = []
                    for doc in summarize_doc:
                        temp_dir = tempfile.mkdtemp()
                        path = os.path.join(temp_dir, doc.name)
                        with open(path, "wb") as f:
                            f.write(doc.getvalue())
                            doc_dir.append(path)
                    response = UploadFile.process_uploaded_files(
                        doc_dir, genai_api_key, rag_with_dropdown
                    )
                    placeholder = st.empty()
                    full_response = ""
                    for item in response:
                        full_response += item
                        placeholder.markdown(full_response)
                    placeholder.markdown(full_response)
            message = {"role": "assistant", "content": full_response}
            st.session_state.messages.append(message)

    def clear_chat_history():
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello. I am SpecWiz - Your personalized architectural assistant! How may I assist you today?",
            }
        ]

    st.sidebar.button("Clear Chat History", on_click=clear_chat_history)

    if prompt := st.chat_input("Ask a question about your ADB documents"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="images/user.png"):
            st.write(prompt)

        # Generate a new response if the last message is not from the assistant
        # if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant", avatar="images/spec.png"):
            with st.spinner("Thinking..."):
                response = ChatBot.respond(prompt, genai_api_key, rag_with_dropdown)
                placeholder = st.empty()
                full_response = ""
                for item in response:
                    full_response += item
                    placeholder.markdown(full_response)
                placeholder.markdown(full_response)
        message = {"role": "assistant", "content": full_response}
        st.session_state.messages.append(message)


if __name__ == "__main__":
    main()
