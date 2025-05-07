## **Folder Structure:**

```
travel-agent-ai/
│
├── backend/                          # Backend folder containing FastAPI and business logic
│   ├── main.py                       # FastAPI app with Socket.IO integration for collaboration
│   ├── itinerary_generator.py        # Logic for generating itineraries
│   ├── vector_store.py               # Logic for interacting with Pinecone
│   ├── prompts/                      # Contains prompt files for LLM enrichment
│   │   ├── system_prompt.txt         # System prompt for the LLM (Gemini API)
│   │   └── weather_rules.txt        # Weather-related rules for itinerary generation
│   ├── data/                         # Data sources for TripAdvisor, geo data, etc.
│   │   ├── tripadvisor_reviews.csv   # TripAdvisor review dataset (via Kaggle)
│   │   ├── lonelyplanet_articles/   # Scraped LonelyPlanet travel articles
│   │   ├── reddit_posts/            # Scraped Reddit posts (r/solotravel)
│   │   ├── historical_prices.csv     # Historical price data from Skyscanner (or simulated)
│   │   └── geo_data.json             # Geo data (city, monuments, restaurants)
│   └── utils/                        # Utility files for external API integrations
│       ├── maps_api.py               # Google Maps API functions (e.g., geocoding, directions)
│       ├── yelp_api.py               # Yelp API functions (for restaurants/activities)
│       ├── weather_api.py            # OpenWeather API functions (for weather-based suggestions)
│       └── stays_api.py              # Functions for Booking/Airbnb stays
│
├── collaborative_workspace/          # Folder for collaborative workspace logic
│   ├── socket_io.py                  # Socket.IO server for collaborative workspace
│   └── collaborative_logic.py        # Logic to handle real-time collaboration
│
├── frontend/                         # Frontend folder (HTML, CSS, JS)
│   └── templates/
│       └── index.html                # Frontend HTML file for collaborative workspace
│
├── models/                           # Folder for fine-tuned LLM models (optional)
│   └── finetuned_travel_model/       # Optional: Folder for storing the custom fine-tuned travel model
│
├── requirements.txt                  # List of dependencies for backend
├── README.md                         # Project documentation
└── .gitignore                        # Git ignore file for ignoring unnecessary files (e.g., venv, node_modules)
```

---

### **Backend Folder (`backend/`)**:

This is where the core logic of the project resides. It handles the API (FastAPI) setup, itinerary generation, data retrieval, and integrates external APIs.

1. **`main.py`**:

   * This file sets up the FastAPI server and manages the routes (API endpoints) for your travel agent.
   * **Socket.IO Integration**: This is critical for collaboration. It listens for requests related to user interactions, updates the itinerary in real-time, and sends updates to all users who are connected.
   * **API Routes**: The FastAPI app exposes endpoints like `GET /generate-itinerary`, `POST /submit-preferences`, which allow users to interact with the backend. These routes invoke functions from `itinerary_generator.py`, which handle the logic for itinerary creation.

2. **`itinerary_generator.py`**:

   * **Core Logic for Generating Itineraries**: This file is the heart of your project. It takes user inputs (preferences, location, date) and generates a personalized itinerary by using data from various sources like TripAdvisor reviews, geo data, and weather rules.
   * **Interacts with Data**: It uses datasets like `tripadvisor_reviews.csv`, `geo_data.json`, and the weather rules defined in `weather_rules.txt` to form suggestions and recommendations for the user.
   * **Integration with External APIs**: This file also connects to external APIs (via functions in `utils/`), such as Google Maps (maps\_api.py) for geocoding or OpenWeather for weather-based suggestions.
   * The generated itineraries are formatted in JSON and returned to the frontend for display.

3. **`vector_store.py`**:

   * **Interacting with Pinecone**: This file integrates Pinecone as your vector database. Pinecone stores vectors for fast retrieval of travel recommendations.
   * **Use Case**: After generating an itinerary, this file can be used to store and retrieve relevant recommendations quickly based on user preferences.

4. **`prompts/`**:

   * **`system_prompt.txt`**: Contains a system-level prompt for your LLM (Gemini API). The system prompt ensures that your LLM understands its role and generates meaningful travel itineraries based on the given input.
   * **`weather_rules.txt`**: Contains rules for suggesting activities based on the weather. For instance, if the weather forecast is clear, you might suggest outdoor activities, whereas if it’s rainy, you might suggest indoor activities like museums.

5. **`data/`**:

   * **`tripadvisor_reviews.csv`**: A CSV file with reviews from TripAdvisor. This can be used for recommending popular attractions or destinations based on user preferences.
   * **`lonelyplanet_articles/`**: A folder containing scraped travel articles from LonelyPlanet. These articles may contain detailed itineraries and tips, which can be parsed and used for itinerary generation.
   * **`reddit_posts/`**: Contains Reddit posts from the `r/solotravel` subreddit. This can be useful for recommendations from real travelers and help inform the generated itinerary with practical tips.
   * **`historical_prices.csv`**: Data related to historical prices of travel-related items (e.g., flights, accommodation). This is important to suggest budget-friendly itineraries based on historical price trends.
   * **`geo_data.json`**: Contains geographic data like city names, tourist attractions, monuments, restaurants, and their locations. This data will be essential for generating personalized itineraries that include location-specific recommendations.

6. **`utils/`**:

   * **`maps_api.py`**: Contains functions to interact with Google Maps API. It can be used for tasks such as finding nearby attractions, getting the location of a restaurant, or calculating travel distances.
   * **`yelp_api.py`**: Functions that interact with Yelp's API. Useful for retrieving restaurant and activity recommendations in a given area.
   * **`weather_api.py`**: This file handles communication with OpenWeather's API, pulling in current weather data and forecasts to suggest weather-appropriate activities.
   * **`stays_api.py`**: Functions to search for stay options through Booking.com or Airbnb. It helps suggest places to stay based on user preferences.

---

### **Collaborative Workspace (`collaborative_workspace/`)**:

This section enables multiple users to collaboratively edit the same travel itinerary in real-time. It's based on **Socket.IO** for real-time communication.

1. **`socket_io.py`**:

   * **Socket.IO Server**: This file sets up a Socket.IO server that listens for events such as itinerary changes, new user joins, or edits. It broadcasts updates to all users in the same session, ensuring the itinerary stays synchronized across all devices.
   * **Real-time Updates**: For example, when one user updates an activity in the itinerary, the update is broadcast to other users in real-time.

2. **`collaborative_logic.py`**:

   * **Managing Collaboration**: Contains the logic that handles user interactions, such as joining the workspace, updating the itinerary, and sending those updates to all connected clients. It manages events like adding a new location, changing a date, or deleting an activity in the itinerary.
   * **Session Management**: Keeps track of user sessions, ensuring that everyone working on the same itinerary is kept up-to-date.

---

### **Frontend (`frontend/`)**:

The frontend folder would contain HTML, CSS, and JavaScript to display and interact with the collaborative workspace. The real-time functionality is driven by the backend and Socket.IO.

* **`index.html`**: This is the main HTML file that will be used for the frontend. It will interact with the backend via API requests and use **Socket.IO** for real-time collaboration. Users can add, remove, or update itinerary items, and all updates will reflect instantly for everyone in the session.

---

### **Models Folder (`models/`)**:

If you decide to fine-tune an LLM (like GPT) for travel-specific tasks, this is where you would store the model files.

* **`finetuned_travel_model/`**: This folder would contain any custom-trained or fine-tuned models (optional). For instance, you could fine-tune a travel-specific LLM model to make better suggestions based on real-world travel data or user inputs.

---

### **Other Files**:

1. **`requirements.txt`**:

   * This is a list of Python dependencies that the project needs to run. For example, dependencies like FastAPI, Socket.IO, Pinecone, and various external API libraries (Google Maps, OpenWeather) would be listed here.
   * By running `pip install -r requirements.txt`, you can set up your environment with the necessary libraries.

2. **`README.md`**:

   * Provides an overview of the project, how to set it up, and how it works. It should also explain how to run the backend, make requests to the API, and use the collaborative features.
   * It also helps other developers or collaborators understand the structure and purpose of the project.

3. **`.gitignore`**:

   * This file ensures that unnecessary files, like temporary files, virtual environments, or node modules, are not tracked by Git. This keeps your repository clean and efficient.

---

### **How It All Connects**:

1. **Backend**: The FastAPI app is the central hub for handling requests. It exposes routes like `GET /generate-itinerary` and `POST /preferences`, which call the logic in `itinerary_generator.py` to generate itineraries. The `vector_store.py` integrates Pinecone for quick search and retrieval of relevant data.

2. **Collaborative Workspace**: The `collaborative_workspace` folder, powered by Socket.IO, ensures that multiple users can edit the itinerary in real-time. When one user adds an activity, removes a place, or changes a detail, the update is pushed to all users connected to the same session.

3. **Real-time Interactions**: Whenever a user updates their preferences or itinerary, the backend generates suggestions using data from the `data/` folder and external APIs (via `utils/`). The frontend updates accordingly, and any changes made in the collaborative workspace are synchronized across users using Socket.IO.

This design ensures that users get real-time personalized travel itineraries based on weather, location, and historical data, while also allowing for collaborative, real-time updates on their travel plans.
