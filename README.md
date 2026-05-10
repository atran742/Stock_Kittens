# Stock_Kittens
An AI agent and application which trades stocks for users, trained on evaluating market data, news, and other trading tools to make the best decisions.


How to Run:

Open a terminal to /frontend and run "npm install" followed by "npm run"

Then, open a second terminal in the root directory and run "uvicorn api.routes:app --reload --host 0.0.0.0 --port 8000"

Then, open one last terminal and type "ollama serve"
