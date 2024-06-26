import os
from utils.prepare_vectordb import PrepareVectorDB
from utils.load_config import LoadConfig
from typing import List, Tuple

CONFIG = LoadConfig()


class UploadDataManually:
    @staticmethod
    def upload_data_manually(files_dir: List, genai_api_key: str) -> Tuple:
        print(files_dir)
        prepare_vectordb_instance = PrepareVectorDB(
            data_directory=files_dir,
            genai_api_key=genai_api_key,
            persist_directory=CONFIG.persist_directory,
            chunk_size=CONFIG.chunk_size,
            chunk_overlap=CONFIG.chunk_overlap,
        )
        if not len(os.listdir(CONFIG.persist_directory)) != 0:
            prepare_vectordb_instance.prepare_and_save_vectordb()
        else:
            print(f"VectorDB already exists in {CONFIG.persist_directory}")
            prepare_vectordb_instance.append_to_vector_db()
            print(f"File successfully added in {CONFIG.persist_directory}")
        result = "Uploaded files are processed. Please ask your question"
        return result


# if __name__ == "__main__":
#     upload_data_manually()
