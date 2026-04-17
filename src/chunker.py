from langchain_text_splitters import RecursiveCharacterTextSplitter

def split_docs(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=120,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    return splitter.split_documents(docs)