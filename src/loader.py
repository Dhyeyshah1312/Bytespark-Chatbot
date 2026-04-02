from langchain_community.document_loaders import PyPDFLoader

def load_data(path):
    loader = PyPDFLoader(path)
    return loader.load()