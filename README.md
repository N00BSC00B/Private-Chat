# Private Chat Application

This is a private chat application built using Flask, Socket.IO, and WebSockets. It allows users to join chat rooms, send encrypted messages, and share media files securely.

## Features

-   **Real-time Communication**: Uses WebSockets for real-time messaging.
-   **Encryption**: Messages are encrypted using RSA encryption.
-   **Media Sharing**: Users can share media files within the chat.
-   **Responsive Design**: The UI is responsive and works well on different screen sizes.

## Technologies Used

-   **Backend**: Flask, Flask-SocketIO, WebSockets, RSA
-   **Frontend**: HTML, CSS, JavaScript
-   **Styling**: Google Fonts, Colorama

## Installation

1. **Clone the repository**:

    ```bash
    git clone https://github.com/N00BSC00B/Private-Chat.git
    cd Private-Chat
    ```

2. **Create a virtual environment**:

    ```bash
    python -m venv venv
    ```

3. **Activate the virtual environment**:

    - On Windows:
        ```bash
        venv\Scripts\activate
        ```
    - On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

4. **Install the dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

5. **Run the server (or use the already configured centralized server)**:

    ```bash
    python server.py
    ```

6. **Run Web Based Flask App or Python Client**

    ```bash
    python WEB/flask-app.py
    ```

    ```bash
    python client.py
    ```

7. **Open your browser and navigate to**:
    ```
    http://localhost:6652
    ```

## File Descriptions

-   **server.py**: The main server-side script that handles WebSocket connections, encryption, and message routing.
-   **client.py**: The command promt based python client to connect to the server.
-   **static/**: Contains static files such as CSS, JavaScript, and images.
    -   **styles.css**: Contains the styles for the application.
    -   **script.js**: Contains the client-side JavaScript for handling WebSocket connections and UI interactions.
    -   **assets/**: Contains image assets and the manifest file for PWA.
-   **templates/**: Contains HTML templates.
    -   **index.html**: The main HTML file for the chat application.
-   **requirements.txt**: Lists the Python dependencies required for the project.

## Usage

1. **Join a Chat Room**: Enter a username and room code to join a chat room.
2. **Send Messages**: Type a message and press Enter or click the send button to send a message.
3. **Share Media**: Use the `/media` command followed by the file path to share media files.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License. See the [`LICENSE`](LICENSE) file for details.
