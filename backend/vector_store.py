import os
import pinecone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')

# Initialize Pinecone vector database securely
if not PINECONE_API_KEY:
    raise ValueError("Pinecone API key is not set in the environment variables.")

pinecone.init(api_key=PINECONE_API_KEY, environment="us-west1-gcp")
index = pinecone.Index("travel-itineraries")

def generate_vector_from_itinerary(itinerary):
    # Placeholder function to convert an itinerary into a vector (you can use embeddings here)
    # Implement your own method of generating vectors based on the itinerary details
    return [0.1, 0.2, 0.3]  # Example vector (replace with real implementation)

def generate_vector_from_preferences(user_preferences):
    # Placeholder function to convert user preferences into a vector
    # Implement your own method of generating vectors based on user preferences
    return [0.1, 0.2, 0.3]  # Example vector (replace with real implementation)

def store_itinerary(itinerary):
    # Store the itinerary vector in Pinecone for retrieval
    try:
        vector = generate_vector_from_itinerary(itinerary)
        index.upsert([(itinerary['destination'], vector)])  # Ensure 'destination' is unique
        print(f"Stored itinerary for {itinerary['destination']}")
    except Exception as e:
        print(f"Error storing itinerary for {itinerary['destination']}: {e}")

def retrieve_similar_itinerary(user_preferences):
    # Retrieve similar itineraries from Pinecone based on user preferences
    try:
        vector = generate_vector_from_preferences(user_preferences)
        results = index.query(vector, top_k=5)
        return results
    except Exception as e:
        print(f"Error retrieving similar itineraries: {e}")
        return []
