from src.helper import load_pdf_file, text_split, download_embeddings, load_excel_as_documents
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv
import os

load_dotenv()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
os.environ['PINECONE_API_KEY'] = PINECONE_API_KEY

# extracted_data = load_pdf_file(data='data/pdfs')
text_chunks = text_split(extracted_data)

# excel_docs = load_excel_as_documents("data/database/museum_events.xlsx")

all_documents = text_chunks + excel_docs

embeddings = download_embeddings()

pc = Pinecone(api_key=PINECONE_API_KEY)

index_name = 'name'

if index_name not in [index.name for index in pc.list_indexes()]:
    pc.create_index(
        name=index_name,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

docsearch = PineconeVectorStore.from_documents(
    documents=all_documents,
    index_name=index_name,
    embedding=embeddings,
)
