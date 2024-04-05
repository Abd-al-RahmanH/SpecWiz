import streamlit as st
from utils.upload_file_v2 import UploadFile
from utils.upload_data_manually_v2 import UploadDataManually
from utils.chatbot_v2 import ChatBot
import tempfile, os
from boxsdk import OAuth2, Client, object, CCGAuth
import os, time
from utils.load_config import LoadConfig
from langchain.vectorstores import Chroma
from utils.prepare_vectordb import PrepareVectorDB

CONFIG = LoadConfig()


st.title("SpecWiz")


def get_box_files():
    auth = CCGAuth(
        client_id="of1ol55q0ecwqkfdwm56j32rxodhfo6p",
        client_secret="Bd81vrsd8RnVJFt3uskiEwn7o9AFumev",
        enterprise_id="455328",
    )
    client = Client(auth)

    folder_items = client.folder(folder_id="257158571352").get_items()
    file_paths = []
    for item in folder_items:
        if isinstance(item, object.file.File):
            file_path = os.path.join(tempfile.mkdtemp(), item.name)
            with open(file_path, "wb") as f:
                item.download_to(f)
            file_paths.append(file_path)
    return file_paths


def main():
    # file_msg = ""
    with st.sidebar:
        st.write(
            "This chatbot is created using IBM WatsonX to chat with PRM ARB Technical Specifications."
        )

        rag_with_dropdown = st.selectbox(
            "Chat with",
            (
                "Preprocessed doc",
                "Upload doc: Process for RAG",
                "Upload doc: Give full summary",
            ),
        )
        if rag_with_dropdown == "Preprocessed doc":
            if not len(os.listdir(CONFIG.persist_directory)) != 0:
                with st.spinner("Getting files from Box"):
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
                            doc_dir
                        )
                        st.success(processed_file_msg)

        elif rag_with_dropdown == "Upload doc: Process for RAG":
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
                file_msg = UploadFile.process_uploaded_files(doc_dir, rag_with_dropdown)
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
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if rag_with_dropdown == "Upload doc: Give full summary":
        if st.sidebar.button("Summarize ADB Document"):
            prompt = "Please summarize my ADB document"
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.write(prompt)

            if st.session_state.messages[-1]["role"] != "assistant":
                with st.chat_message("assistant"):
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
                            doc_dir, rag_with_dropdown
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

    # gen_ai_key = st.text_input("Enter your IBM WatsonX API Key", "")

    # if gen_ai_key:

    if prompt := st.chat_input("Ask a question about your ADB documents"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.write(prompt)

    # Generate a new response if last message is not from assistant
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = ChatBot.respond(prompt, rag_with_dropdown)
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
