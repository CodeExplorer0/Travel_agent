from flask import Flask, render_template, request
from src.helper import download_embeddings, book_tickets, is_meta_question, is_museum_related,is_price_query,get_ticket_price_info
from langchain_pinecone import PineconeVectorStore
from langchain_ollama import OllamaLLM  # ✅ Updated import
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import *
import os
from src.booking import handle_booking

app = Flask(__name__)

# Load environment variables
load_dotenv()
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY')
os.environ['PINECONE_API_KEY'] = PINECONE_API_KEY
os.environ['HUGGINGFACE_API_KEY'] = HUGGINGFACE_API_KEY

# Load embeddings and index
embeddings = download_embeddings()
index_name = 'name'
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)
retriever = docsearch.as_retriever(search_type='similarity', search_kwargs={"k": 3})

llm = OllamaLLM(model="mistral:7b-instruct-q4_0") 
# llm=OllamaLLM(model="phi")
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])
qa_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, qa_chain)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    input_text = msg.lower()
    print("User Input:", input_text)

    # if is_meta_question(input_text):
    #     return "error message"


    # if is_price_query(input_text):
    #     return get_ticket_price_info()

    # ✅ Now limit booking logic to actual booking queries
    # if "book" in input_text:
    #     try:
    #         words = input_text.split()
    #         if "for" in words:
    #             idx = words.index("for")
    #             event_name = " ".join(words[idx + 1:])
    #         else:
    #             return "⚠️ Please specify the event name, e.g. 'Book 2 tickets for Secrets of the Mummy'."

    #         num = [int(s) for s in words if s.isdigit()]
    #         num_tickets = num[0] if num else 1

    #         print(f"Detected booking intent: {num_tickets} tickets for {event_name.title()}")
    #         booking_response = handle_booking(event_name.title(), num_tickets)
    #         return booking_response

    #     except Exception as e:
    #         print("Booking Error:", e)
    #         return "⚠️ Sorry, I couldn’t process your booking. Try something like: 'Book 2 tickets for Secrets of the Mummy'."

    # if not is_museum_related(input_text):
    #     return "Hello I'm Museo , your assistant for your Indian Museum trip!!" \
    #            "I can help you with \nInformation about the museum \nbooking of tickets for events\n" \
    #            "⚠️ Please specify the event name, e.g. 'Book 2 tickets for Secrets of the Mummy'."

    # response = rag_chain.invoke({"input": msg})
    # print("Response:", response["answer"])
    # return str(response["answer"])

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
