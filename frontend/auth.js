// Change this to your FastAPI backend URL
const API_URL = "http://127.0.0.1:8000";

// ======================
// SIGNUP
// ======================
async function signup() {

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (!name || !email || !password || !confirmPassword) {
        alert("Please fill all fields.");
        return;
    }

    if (password !== confirmPassword) {
        alert("Passwords do not match.");
        return;
    }

    try {

        const response = await fetch(`${API_URL}/auth/register`, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                full_name: name,
                email,
                password
            })
        });

        const data = await response.json();
        if (response.ok) {
            alert("Account created successfully!");
            window.location.href = "login.html";
        } else {
            alert(data.detail || "Signup failed");
        }
    } catch (err) {
        alert("Cannot connect to server.");
    }

}


// ======================
// LOGIN
// ======================
async function login() {
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    if (!email || !password) {
        alert("Please fill all fields.");
        return;
    }

    try {

        const response = await fetch(`${API_URL}/auth/login`, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                email,
                password
            })

        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem("token", data.access_token);
            localStorage.setItem("user", data.full_name);
            window.location.href = "index.html";
        } else {
            alert(data.detail || "Invalid credentials");
        }
        } catch (err) {
        alert("Cannot connect to server.");
        }
    }


// ======================
// LOGOUT
// ======================
function logoutUser() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "login.html";
}


// ======================
// CHECK LOGIN
// ======================
function checkLogin() {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
    }
}

function loadUser() {
    const user = localStorage.getItem("user");
    if (!user) return;
    const welcome = document.getElementById("welcome-user");
    if (welcome) {
        welcome.innerHTML = `👋 Welcome, <b>${user}</b>`;
    }
}