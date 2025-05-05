from flask import Flask, render_template, request
from src.helper import download_embeddings, book_tickets, is_meta_question, is_museum_related, is_price_query, get_ticket_price_info
from langchain_pinecone import PineconeVectorStore
from langchain_ollama import OllamaLLM  # ✅ Updated import
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.booking import handle_booking
import os

app = Flask(__name__)

# Load environment variables
load_dotenv()

# It's better to access environment variables directly after loading them
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY')

# Ensure that the API keys are set
if not PINECONE_API_KEY or not HUGGINGFACE_API_KEY:
    raise ValueError("API keys for Pinecone and HuggingFace must be set in the .env file.")

# Load embeddings and index
embeddings = download_embeddings()
index_name = 'name'

try:
    docsearch = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embeddings)
    retriever = docsearch.as_retriever(search_type='similarity', search_kwargs={"k": 3})
except Exception as e:
    raise ValueError(f"Error loading Pinecone index: {e}")

# Initialize LLM
llm = OllamaLLM(model="mistral:7b-instruct-q4_0")  # You can swap out the model as needed
prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

# Setup the chains
qa_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, qa_chain)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/get", methods=["GET", "POST"])
def chat():
    try:
        msg = request.form["msg"]
        input_text = msg.strip().lower()  # Removing extra spaces and handling lowercase

        print("User Input:", input_text)

        # Handle meta questions or pricing logic if needed
        # Uncomment or modify the following as per your requirements
        # if is_meta_question(input_text):
        #     return "error message"
        
        # if is_price_query(input_text):
        #     return get_ticket_price_info()

        # Example of using the RAG chain to generate responses
        response = rag_chain.invoke({"input": msg})
        print("Response:", response["answer"])
        return str(response["answer"])

    except Exception as e:
        print("Error during processing:", e)
        return "Sorry, something went wrong. Please try again later."

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
