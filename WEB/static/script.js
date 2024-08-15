const socket = io.connect();

const notification = document.getElementById('notification-container');

let firstRun = true;
let is409Error = false;
let connected = false;
let username;
let room;

// Function to send a message via WebSocket
function sendMessage(message) {
    let data = { room: room, username: username, message: message };
    console.log(data);
    socket.emit('send_message', data);
    updateChat(message, 'YOU');
}

// Function to initialize WebSocket connection after user submits username and room
function initializeWebSocket(newUsername, newRoom) {
    if (newUsername !== "" && newRoom !== "") {

        username = newUsername;
        room = newRoom;

        // Emit the 'join' event with updated data
        let data = { room: room, username: username };
        socket.emit('join', data);
        connected = true;

    } else {
        console.error("Username and room are required");
        socket.close();
    }
}

// Function to read user input and send messages
function startReadingInput() {
    const inputField = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');

    inputField.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); // Prevent the default behavior of Enter key
            // check if empty message
            if (inputField.value.trim() === '') {
                return;
            }
            sendMessage(inputField.value);
            inputField.value = ''; // Clear input field after sending
        }
    });

    sendButton.addEventListener('click', function () {
        sendMessage(inputField.value.trim());
        inputField.value = ''; // Clear input field after sending
    });
}


function updateChat(message, type) {
    const chatMessages = document.getElementById('chat-messages');
    const messageContainer = document.createElement('div');
    const messageElement = document.createElement('div');

    if (type === 'SYSTEM_MESSAGE') {
        // Message is a system message (e.g., [INFO], [ERROR], [JOIN], [LEAVE])
        messageContainer.classList.add('message', 'system');
    } else if (type === 'YOU') {
        // Message is sent by the current user
        messageContainer.classList.add('message', 'sender-container');
        messageElement.classList.add('message', 'sender');
    } else {
        // Message is received from another user
        messageContainer.classList.add('message', 'receiver-container');
        messageElement.classList.add('message', 'receiver');
    }
    messageElement.style.whiteSpace = 'pre-wrap';

    messageElement.textContent = message;

    // Append message to message container
    messageContainer.appendChild(messageElement);
    // Append message container to chat container
    chatMessages.appendChild(messageContainer);
    // Scroll to the bottom of the chat container
    chatMessages.scrollTop = chatMessages.scrollHeight;
}



// Event listener for submitting the username and room
document.getElementById('login-form').addEventListener('submit', function (event) {
    event.preventDefault();
    const username = document.getElementById('username').value.trim();
    const roomCode = document.getElementById('room-code').value.trim();
    initializeWebSocket(username, roomCode);
});


socket.on('message_received', function (data) {
    if (data.type === 'SYSTEM_MESSAGE') {
        if (data.code === 409) {
            is409Error = true; // Set is409Error to true if it's a 409 error

            const notificationMessage = document.getElementById('notification-message');
            notificationMessage.textContent = data.message;
            notification.classList.remove('hidden');

            // Remove the notification after a certain duration (e.g., 5 seconds)
            setTimeout(() => {
                notificationMessage.textContent = '';
                notification.classList.add('hidden');
            }, 5000); // 5000 milliseconds (5 seconds)

        } else {
            updateChat(data.message, 'SYSTEM_MESSAGE');
        }
        // Check if it's the first run and not a 409 error
        if (firstRun && !is409Error) {
            document.getElementById('user-form').style.display = 'none';
            document.getElementById('chat-container').style.display = 'block';
            firstRun = false; // Update firstRun to false after the first run
            startReadingInput(data.room, data.username);
        }
    } else {
        updateChat(`${data.username}: ${data.message}`, 'OTHERS');
    }
});

window.addEventListener('beforeunload', function (event) {
    userDisconnect();
});

function userDisconnect() {

    let inputData = { room: room, username: username };

    fetch('user_disconnect', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ data: inputData })
    })
        .then(response => response.json())
        .then(data => {
            console.log(data.message);
        })
        .catch(error => {
            console.error('Error sending data:', error);
        });
}
