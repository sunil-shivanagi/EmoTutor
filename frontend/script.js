// 🎨 Reusable inline icons (replace emoji for a cleaner, professional look)
const ICON_SPEAKER = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>`;
const ICON_PAUSE   = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>`;
const ICON_PLAY     = `<svg viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>`;
const ICON_COPY     = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
const ICON_CHECK    = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
const ICON_THUMBS_UP   = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>`;
const ICON_THUMBS_DOWN = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path></svg>`;
let currentCard = 0;
let showingAnswer = false;
let currentPdfId = null;
let currentLearningTopic = null;

if (!localStorage.getItem("token")) {
    window.location.href = "login.html";
}

document.addEventListener("DOMContentLoaded", async () => {
    checkLogin();
    loadUser();
    await loadSessions();
    await loadPDFs();
    const lastSession = localStorage.getItem("lastSession");

    if (lastSession) {
        openSession(lastSession);
    }
});

// 🔊 Update the tts-btn's icon + label together (keeps markup structure intact)
function setTTSButtonState(button, icon, label){
    button.innerHTML = `<span class="btn-icon">${icon}</span><span class="btn-label">${label}</span>`;
}

function getToken() {
    return localStorage.getItem("token");
}

// 🔊 TTS state
let isSpeaking = false;
let isPaused  = false;
let voices    = [];

// Sentence-level tracking
let sentences       = [];
let currentSentence = 0;
let activeButton    = null;

// 📚 Track learning context
let lastChatTopic = "";
let pdfUploaded   = false;
let pdfFileName   = "";
// 📚 Chat topic tracking
let chatTopics = [];  // stores all questions student asked
let currentEmotion = "neutral";
let currentSessionId = null;
let currentStudySessionId = null;
let readingTimer = null;

// Pre-load voices as soon as page loads
window.speechSynthesis.onvoiceschanged = () => {
    voices = window.speechSynthesis.getVoices();
};

// 🎯 Send on Enter
document.getElementById("user-input").addEventListener("keypress", function(e) {
    if (e.key === "Enter") {
        sendMessage();
    }
});

async function createNewSession(pdfId = null) {
    try {
        const response = await fetch(`${API_URL}/session/new`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${getToken()}`
            },
            body: JSON.stringify({
                pdf_id: pdfId
            })
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error);
        }

        const data = await response.json();

        currentSessionId = data.session_id;
        currentPdfId = data.pdf_id ?? null;

        localStorage.setItem(
            "lastSession",
            currentSessionId
        );

        console.log(
            "New Session:",
            currentSessionId,
            "PDF:",
            currentPdfId
        );

        await loadSessions();

        document.getElementById("chat-box").innerHTML = `
            <div class="welcome">
                <h2>Hello! I'm your AI Tutor</h2>
                <p>I detect how you're feeling and adapt explanations.</p>
            </div>
        `;

    } catch (err) {
        console.error(
            "Failed to create session:",
            err
        );

        alert("Could not create chat session.");
    }
}

async function loadSessions() {
    try{
        const response = await fetch(`${API_URL}/session/list`,{
            headers:{
                Authorization:`Bearer ${getToken()}`
            }
        });
        const sessions = await response.json();
        const container = document.getElementById("sessions-container");
        container.innerHTML="";
        sessions.forEach(session=>{
            container.innerHTML += `
                <div class="session-item">

    <div class="session-info" onclick="openSession(${session.id})">
        <strong>${session.title}</strong>
        <small>${session.created_at}</small>
    </div>

    <button class="delete-session"
            onclick="deleteSession(${session.id}, event)">
        🗑️
    </button>

</div>
            `;
        });
    }
    catch(err){
        console.log(err);
    }
}

// 💬 MAIN CHAT FUNCTION
async function sendMessage() {

    let inputField =
        document.getElementById("user-input");

    let input =
        inputField.value.trim();

    if (!input) return;

    addMessage(input, "user");

    inputField.value = "";

    chatTopics.push(input);

    let loadingId =
        addTypingIndicator();

    // Create normal session if needed
    if (!currentSessionId) {

        try {

            await createNewSession();

        } catch (err) {

            console.error(
                "Failed to create session:",
                err
            );

            updateMessage(
                loadingId,
                "❌ Could not create chat session",
                ""
            );

            return;
        }
    }

    try {

        const bodyData = {
            message: input,
            emotion: currentEmotion,
            session_id: currentSessionId
        };

        console.log(
            "Sending chat:",
            bodyData
        );

        const res = await fetch(
            `${API_URL}/chat`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "Authorization":
                        `Bearer ${getToken()}`
                },

                body: JSON.stringify(
                    bodyData
                )
            }
        );

        if (!res.ok) {

            const errorText =
                await res.text();

            throw new Error(
                `HTTP ${res.status}: ${errorText}`
            );
        }

        const data =
            await res.json();

        console.log(
            "CHAT RESPONSE:",
            data
        );

        const reply =
            data.reply ||
            data.answer ||
            "No response";

        if (data.session_id) {

            currentSessionId =
                data.session_id;
        }

        if (readingTimer) {

            clearTimeout(
                readingTimer
            );
        }

        if (
            data.reading_time &&
            data.study_session_id
        ) {

            currentStudySessionId =
                data.study_session_id;

            readingTimer = setTimeout(
                checkStudyResult,
                data.reading_time * 1000
            );
        }

        lastChatTopic = input;

    const plainText =
        data.plain_text ||
        reply
            .replace(/<[^>]*>/g, "")
            .replace(/\*\*\*/g, "")
            .replace(/\*\*/g, "")
            .replace(/#{1,6}\s/g, "")
            .replace(/`{1,3}/g, "")
            .replace(/\n+/g, " ")
            .trim();

    console.log("ABOUT TO UPDATE UI");
    console.log("loadingId:", loadingId);
    console.log("reply:", reply);

        updateMessage(
            loadingId,
            reply,
            plainText
        );

    } catch (error) {

        console.error(
            "Chat error:",
            error
        );

        updateMessage(
            loadingId,
            "❌ Error connecting to server",
            ""
        );
    }
}
// 📄 Upload PDF
async function uploadPDF() {
    let fileInput = document.getElementById("pdf-file");

    if (!fileInput.files[0]) {
        alert("Select a PDF first!");
        return;
    }

    let formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
        const res = await fetch(`${API_URL}/upload-pdf`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${getToken()}`
            },
            body: formData
        });
        const data = await res.json();
        console.log("UPLOAD RESPONSE:", data);
        await loadPDFs();
        
        // Create a fresh chat attached to this PDF
        await createNewSession(
            data.pdf_id
        );
        console.log("Current PDF:", currentPdfId);
        alert("✅ PDF uploaded successfully!");
        pdfUploaded = true;
        pdfFileName = fileInput.files[0].name;
        document.querySelector(".upload-icon").innerHTML=ICON_CHECK;
        document.getElementById("quiz-trigger-btn").innerText =`📝 Quiz — ${pdfFileName.replace(".pdf", "")}`;
         // 👇 Show quiz button after upload
        //document.getElementById("quiz-trigger").style.display = "block";
    } catch (error) {
        alert("❌ Error uploading PDF");
    }
}

// 📎 Show selected filename as a tooltip as soon as a file is chosen
document
.getElementById("pdf-file")
.addEventListener("change",function(){
    if(this.files.length){
        document.querySelector(".upload-btn").title=this.files[0].name;
    }
});

async function detectEmotionFromCamera() {
    const video = document.getElementById("video");

    if (!video || !currentSessionId) return;

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    const blob = await new Promise(resolve =>
        canvas.toBlob(resolve, "image/jpeg")
    );

    const formData = new FormData();
    formData.append("file", blob, "frame.jpg");
    // formData.append("session_id", currentSessionId);
    formData.append("session_id", currentStudySessionId);

    try {
        let res = await fetch(`${API_URL}/detect-emotion`, {
            method: "POST",
            body: formData
        });

        let data = await res.json();
        console.log("Emotion API:", data);
        currentEmotion = data.emotion;
        document.querySelector(".emotion-btn .emotion-text").innerText = currentEmotion;
        // document.querySelector(".emotion .emotion-text").innerText = currentEmotion;
        
        // document.getElementById("emotion-display").innerText = currentEmotion;
        if (data.emotion === "drowsy") {
            if (!document.querySelector(".tutor-popup")) {
                showTutorSuggestion("drowsy", "break");
            }
        }
    } catch (err) {
        console.log(err);
    }
}


// ✂️ Split text into sentences
function splitSentences(text) {
    return text
        .match(/[^.!?]+[.!?]*/g)
        ?.map(s => s.trim())
        .filter(s => s.length > 0)
        || [text];
}

// 🔊 Speak from a specific sentence index
function speakFrom(index) {

    if (index >= sentences.length) {
        // All done
        isSpeaking = false;
        isPaused   = false;
        currentSentence = 0;
        if (activeButton) setTTSButtonState(activeButton, ICON_SPEAKER, "Listen");
        return;
    }

    let utterance = new SpeechSynthesisUtterance(sentences[index]);
    utterance.rate   = 0.95;
    utterance.pitch  = 1.0;
    utterance.volume = 1.0;

    let preferred = voices.find(v => v.lang === "en-US") ||
                    voices.find(v => v.lang.startsWith("en")) ||
                    voices[0];

    if (preferred) utterance.voice = preferred;

    utterance.onend = () => {
        currentSentence++;
        if (!isPaused) {
            speakFrom(currentSentence);
        }
    };

    utterance.onerror = (e) => {
        console.error("TTS Error:", e);
        isSpeaking = false;
        if (activeButton) setTTSButtonState(activeButton, ICON_SPEAKER, "Listen");
    };

    window.speechSynthesis.speak(utterance);
}

// 🔊 MAIN PLAY / PAUSE FUNCTION
function playAudio(text, button) {

    if (!text || text.trim() === "") {
        setTTSButtonState(button, ICON_SPEAKER, "No text");
        return;
    }

    // If this is a NEW message — stop any current speech first
    if (activeButton && activeButton !== button) {
        window.speechSynthesis.cancel();
        setTTSButtonState(activeButton, ICON_SPEAKER, "Listen");
        isSpeaking = false;
        isPaused   = false;
        currentSentence = 0;
    }

    activeButton = button;

    // PAUSE
    if (isSpeaking && !isPaused) {
        window.speechSynthesis.cancel();  // cancel current sentence
        isPaused  = true;
        isSpeaking = false;
        setTTSButtonState(button, ICON_PLAY, "Resume");
        return;
    }

    // RESUME from where we paused
    if (isPaused) {
        isPaused   = false;
        isSpeaking = true;
        setTTSButtonState(button, ICON_PAUSE, "Pause");
        speakFrom(currentSentence);
        return;
    }

    // FRESH START
    sentences       = splitSentences(text);
    currentSentence = 0;
    isSpeaking      = true;
    isPaused        = false;
    setTTSButtonState(button, ICON_PAUSE, "Pause");

    speakFrom(0);
}

// ⌨️ Show animated typing indicator
function addTypingIndicator(){
    let chat=document.getElementById("chat-box");
    let id="typing-"+Date.now();
    let div=document.createElement("div");
    div.className="message bot";
    div.id=id;
    div.innerHTML=`
    <div class="message-content">
        <div class="thinking-box">
            🤖 AI is thinking...
            <div class="typing">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    </div>
    `;
    chat.appendChild(div);
    chat.scrollTop=chat.scrollHeight;
    return id;
}

// 🧾 Add message to chat
function addMessage(text, type) {

    let chatBox = document.getElementById("chat-box");
    let id = "msg-" + Date.now();

    let div = document.createElement("div");
    div.classList.add("message", type);
    div.id = id;

    div.innerHTML = `
        <p>${text}</p>
        <small>${getTime()}</small>
    `;

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;

    return id;
}


// 🔄 Update message with Play button

function updateMessage(id, newText, ttsText = "") {

    console.log("updateMessage called:", id);

    const div = document.getElementById(id);

    if (!div) {
        console.error("Typing element NOT FOUND:", id);
        return;
    }

    console.log("Typing element found:", div);

    try {

        let renderedText;

        if (typeof marked !== "undefined") {
            renderedText = marked.parse(newText);
        } else {
            console.warn("marked.js not available");
            renderedText = newText.replace(/\n/g, "<br>");
        }

        div.innerHTML = `
            <div class="message-content">
                <div class="markdown-body">
                    ${renderedText}
                </div>

                <div class="msg-footer">
                    <div class="action-buttons">

                        <button class="tts-btn">
                            <span class="btn-icon">${ICON_SPEAKER}</span>
                            <span class="btn-label">Listen</span>
                        </button>

                        <button class="copy-btn">
                            <span class="btn-icon">${ICON_COPY}</span>
                            <span class="btn-label">Copy</span>
                        </button>

                        <button class="like-btn" title="Good response">
                            ${ICON_THUMBS_UP}
                        </button>

                        <button class="dislike-btn" title="Bad response">
                            ${ICON_THUMBS_DOWN}
                        </button>

                    </div>

                    <small>${getTime()}</small>
                </div>
            </div>
        `;

        // ---------------------------------------------
        // TTS
        // ---------------------------------------------

        const btn = div.querySelector(".tts-btn");

        if (btn) {
            btn.addEventListener("click", () => {
                playAudio(ttsText, btn);
            });
        }

        // ---------------------------------------------
        // Copy
        // ---------------------------------------------

        const copyBtn = div.querySelector(".copy-btn");

        if (copyBtn) {

            copyBtn.onclick = async () => {

                try {

                    await navigator.clipboard.writeText(ttsText);

                    copyBtn.innerHTML = `
                        <span class="btn-icon">${ICON_CHECK}</span>
                        <span class="btn-label">Copied</span>
                    `;

                    setTimeout(() => {

                        copyBtn.innerHTML = `
                            <span class="btn-icon">${ICON_COPY}</span>
                            <span class="btn-label">Copy</span>
                        `;

                    }, 1500);

                } catch (error) {

                    console.error(
                        "Copy failed:",
                        error
                    );

                }
            };
        }

        // ---------------------------------------------
        // Highlight code
        // ---------------------------------------------

        if (typeof hljs !== "undefined") {

            div.querySelectorAll("pre code").forEach(block => {

                try {
                    hljs.highlightElement(block);
                } catch (error) {
                    console.warn(
                        "Code highlighting failed:",
                        error
                    );
                }

            });

        }

        // ---------------------------------------------
        // Scroll
        // ---------------------------------------------

        const chatBox =
            document.getElementById("chat-box");

        if (chatBox) {

            chatBox.scrollTo({
                top: chatBox.scrollHeight,
                behavior: "smooth"
            });

        }

        console.log("Message successfully rendered.");

    } catch (error) {

        console.error(
            "updateMessage ERROR:",
            error
        );

        // ---------------------------------------------
        // IMPORTANT:
        // Even if markdown/TTS/etc. fails,
        // don't leave "AI is thinking..."
        // ---------------------------------------------

        div.innerHTML = `
            <div class="message-content">
                <div class="markdown-body">
                    ${newText.replace(/\n/g, "<br>")}
                </div>
            </div>
        `;
    }
}


// 🕒 Get current time
function getTime() {
    let now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}


// ========== QUIZ FUNCTIONS ==========

let quizData = [];

async function openQuizModal() {

    document.getElementById("quiz-modal").style.display = "flex";
    document.getElementById("quiz-setup").style.display = "block";
    document.getElementById("quiz-questions").style.display = "none";
    document.getElementById("quiz-results").style.display = "none";
    document.getElementById("quiz-loading").style.display = "none";

    const chatLabel =
        document.getElementById("src-chat-label");

    const topicListDiv =
        document.getElementById("chat-topic-list");

    // -----------------------------------------------------
    // Load topics from database
    // -----------------------------------------------------

    if (!currentSessionId) {

        chatLabel.style.display = "none";

    } else {

        try {

            const response = await fetch(
                `${API_URL}/session/${currentSessionId}/topics`,
                {
                    headers: {
                        "Authorization":
                            `Bearer ${getToken()}`
                    }
                }
            );

            if (!response.ok) {
                throw new Error(
                    "Failed to load learning topics"
                );
            }

            const data = await response.json();

            const topics = data.topics || [];

            if (topics.length > 0) {

                chatLabel.style.display = "flex";

                const options = topics
                    .map(topic => {

                        const currentLabel =
                            topic.is_current
                                ? " (Current)"
                                : "";

                        return `
                            <option value="${topic.id}">
                                ${topic.topic}${currentLabel}
                            </option>
                        `;
                    })
                    .join("");

                topicListDiv.innerHTML = `
                    <select
                        id="chat-topic-select"
                        style="
                            width:100%;
                            padding:8px;
                            margin-top:6px;
                            border:1px solid #ddd;
                            border-radius:6px;
                            font-size:13px;
                        "
                    >
                        ${options}
                    </select>
                `;

                // Automatically select current topic
                const currentTopic =
                    topics.find(
                        topic => topic.is_current
                    );

                if (currentTopic) {

                    document.getElementById(
                        "chat-topic-select"
                    ).value = currentTopic.id;
                }

            } else {

                chatLabel.style.display = "none";

            }

        } catch (error) {

            console.error(
                "Failed to load topics:",
                error
            );

            chatLabel.style.display = "none";
        }
    }

    // -----------------------------------------------------
    // PDF option
    // -----------------------------------------------------

    const pdfLabel =
        document.getElementById("src-pdf-label");

    if (pdfUploaded) {

        pdfLabel.style.display = "flex";

        document.getElementById(
            "pdf-name-preview"
        ).innerText = pdfFileName;

    } else {

        pdfLabel.style.display = "none";
    }

    // -----------------------------------------------------
    // Automatically choose best source
    // -----------------------------------------------------

    if (pdfUploaded) {

        document.querySelector(
            'input[name="quiz-source"][value="pdf"]'
        ).checked = true;

        document.getElementById(
            "custom-topic-div"
        ).style.display = "none";

    } else if (currentSessionId) {

        const topicsResponse =
            await fetch(
                `${API_URL}/session/${currentSessionId}/topics`,
                {
                    headers: {
                        "Authorization":
                            `Bearer ${getToken()}`
                    }
                }
            );

        if (topicsResponse.ok) {

            const topicsData =
                await topicsResponse.json();

            if (
                topicsData.topics &&
                topicsData.topics.length > 0
            ) {

                document.querySelector(
                    'input[name="quiz-source"][value="chat"]'
                ).checked = true;

                document.getElementById(
                    "custom-topic-div"
                ).style.display = "none";

            } else {

                document.querySelector(
                    'input[name="quiz-source"][value="custom"]'
                ).checked = true;

                document.getElementById(
                    "custom-topic-div"
                ).style.display = "block";
            }
        }

    } else {

        document.querySelector(
            'input[name="quiz-source"][value="custom"]'
        ).checked = true;

        document.getElementById(
            "custom-topic-div"
        ).style.display = "block";
    }

    // -----------------------------------------------------
    // Source radio buttons
    // -----------------------------------------------------

    document
        .querySelectorAll(
            'input[name="quiz-source"]'
        )
        .forEach(radio => {

            radio.addEventListener(
                "change",
                () => {

                    const value =
                        document.querySelector(
                            'input[name="quiz-source"]:checked'
                        ).value;

                    document.getElementById(
                        "custom-topic-div"
                    ).style.display =
                        value === "custom"
                            ? "block"
                            : "none";
                }
            );
        });
}


function closeQuizModal() {
    document.getElementById("quiz-modal").style.display = "none";
}

async function startQuiz() {

    const source =
        document.querySelector(
            'input[name="quiz-source"]:checked'
        )?.value || "custom";

    const type =
        document.getElementById(
            "quiz-type"
        ).value;

    const num =
        parseInt(
            document.getElementById(
                "quiz-num"
            ).value
        );

    let topic = null;
    let topicId = null;

    // -----------------------------------------------------
    // Stored learning topic
    // -----------------------------------------------------

    if (source === "chat") {

        const select =
            document.getElementById(
                "chat-topic-select"
            );

        if (!select || !select.value) {

            alert(
                "No learning topic available."
            );

            return;
        }

        topicId =
            parseInt(select.value);

    }

    // -----------------------------------------------------
    // PDF
    //
    // We still use the selected learning topic
    // to search inside the PDF.
    // -----------------------------------------------------

    else if (source === "pdf") {

        const select =
            document.getElementById(
                "chat-topic-select"
            );

        if (select && select.value) {

            topicId =
                parseInt(select.value);

        } else {

            alert(
                "Please discuss a topic before taking a PDF quiz."
            );

            return;
        }
    }

    // -----------------------------------------------------
    // Custom topic
    // -----------------------------------------------------

    else {

        topic =
            document.getElementById(
                "quiz-topic"
            ).value.trim();

        if (!topic) {

            alert(
                "Please enter a topic!"
            );

            return;
        }
    }

    // -----------------------------------------------------
    // Show loading
    // -----------------------------------------------------

    document.getElementById(
        "quiz-loading"
    ).style.display = "block";

    try {

        const response =
            await fetch(
                `${API_URL}/generate-quiz`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Authorization":
                            `Bearer ${getToken()}`
                    },

                    body: JSON.stringify({

                        topic: topic,

                        topic_id: topicId,

                        session_id:
                            currentSessionId,

                        quiz_type: type,

                        num_questions: num,

                        use_pdf:
                            source === "pdf"
                    })
                }
            );

        if (!response.ok) {

            const errorText =
                await response.text();

            throw new Error(
                `HTTP ${response.status}: ${errorText}`
            );
        }

        const data =
            await response.json();

        console.log(
            "QUIZ RESPONSE:",
            data
        );

        quizData =
            data.quiz || [];

        if (
            !quizData ||
            quizData.length === 0
        ) {

            alert(
                "Could not generate quiz. Try another topic."
            );

            return;
        }

        // -------------------------------------------------
        // Use topic returned by backend
        // -------------------------------------------------

        const finalTopic =
            data.topic ||
            topic ||
            "Selected Topic";

        renderQuiz(
            finalTopic,
            type
        );

    } catch (error) {

        console.error(
            "Quiz generation error:",
            error
        );

        alert(
            "❌ Error generating quiz"
        );

    } finally {

        document.getElementById(
            "quiz-loading"
        ).style.display = "none";
    }
}


function renderQuiz(topic, type) {

    document.getElementById("quiz-setup").style.display     = "none";
    document.getElementById("quiz-questions").style.display = "block";
    document.getElementById("quiz-meta").innerText =
        `Topic: ${topic} • ${quizData.length} Questions`;

    let container = document.getElementById("questions-container");
    container.innerHTML = "";

    quizData.forEach((q, i) => {

        let html = `<div class="quiz-question" style="margin-bottom:24px; 
                        padding:16px; background:#f9f9f9; border-radius:10px;">
                        <p style="font-weight:bold; margin-bottom:10px;">
                            Q${i + 1}. ${q.question}
                        </p>`;

        if (q.type === "mcq") {
            Object.entries(q.options).forEach(([key, val]) => {
                html += `
                    <label style="display:block; margin:6px 0; cursor:pointer;">
                        <input type="radio" name="q${i}" value="${key}"
                               style="margin-right:8px;">
                        <strong>${key}.</strong> ${val}
                    </label>`;
            });

        } else if (q.type === "truefalse") {
            html += `
                <label style="margin-right:20px; cursor:pointer;">
                    <input type="radio" name="q${i}" value="True"
                           style="margin-right:6px;"> True
                </label>
                <label style="cursor:pointer;">
                    <input type="radio" name="q${i}" value="False"
                           style="margin-right:6px;"> False
                </label>`;

        } else if (q.type === "shortanswer") {
            html += `
                <input type="text" id="short-${i}"
                       placeholder="Type your answer..."
                       style="width:100%; padding:8px; border:1px solid #ddd;
                              border-radius:6px; font-size:14px;"/>`;
        }

        html += `</div>`;
        container.innerHTML += html;
    });
}

function submitQuiz() {

    let score  = 0;
    let review = "";

    quizData.forEach((q, i) => {

        let userAnswer = "";

        if (q.type === "mcq" || q.type === "truefalse") {
            let selected = document.querySelector(`input[name="q${i}"]:checked`);
            userAnswer = selected ? selected.value : "No answer";
        } else if (q.type === "shortanswer") {
            userAnswer = document.getElementById(`short-${i}`)?.value.trim() || "No answer";
        }

        let correct = userAnswer.toLowerCase().trim() === q.answer.toLowerCase().trim();
        if (correct) score++;

        let borderColor = correct ? "#4CAF50" : "#f44336";

        review += `
            <div style="margin-bottom:20px; padding:14px;
                        border-left:4px solid ${borderColor};
                        background:#fafafa; border-radius:8px;">
                <p style="font-weight:bold; margin-bottom:10px;">
                    Q${i+1}. ${q.question}
                </p>`;

        // MCQ — show all options with highlights
        if (q.type === "mcq" && q.options) {
            Object.entries(q.options).forEach(([key, val]) => {

                let isCorrect  = key.toLowerCase() === q.answer.toLowerCase();
                let isSelected = key.toLowerCase() === userAnswer.toLowerCase();

                let bg     = "";
                let icon   = "";
                let weight = "normal";

                if (isCorrect) {
                    bg   = "background:#e6f9e6;";
                    icon = " ✅";
                    weight = "bold";
                }
                if (isSelected && !isCorrect) {
                    bg   = "background:#fde8e8;";
                    icon = " ❌";
                    weight = "bold";
                }

                review += `
                    <div style="padding:6px 10px; margin:4px 0;
                                border-radius:6px; ${bg} font-weight:${weight};">
                        <strong>${key}.</strong> ${val}${icon}
                    </div>`;
            });

        // True/False — show both options with highlights
        } else if (q.type === "truefalse") {
            ["True", "False"].forEach(option => {

                let isCorrect  = option.toLowerCase() === q.answer.toLowerCase();
                let isSelected = option.toLowerCase() === userAnswer.toLowerCase();

                let bg   = "";
                let icon = "";
                let weight = "normal";

                if (isCorrect) {
                    bg   = "background:#e6f9e6;";
                    icon = " ✅";
                    weight = "bold";
                }
                if (isSelected && !isCorrect) {
                    bg   = "background:#fde8e8;";
                    icon = " ❌";
                    weight = "bold";
                }

                review += `
                    <div style="padding:6px 10px; margin:4px 0;
                                border-radius:6px; ${bg} font-weight:${weight};">
                        ${option}${icon}
                    </div>`;
            });

        // Short answer — show user answer vs correct
        } else if (q.type === "shortanswer") {
            review += `
                <div style="padding:6px 10px; margin:4px 0; border-radius:6px;
                            background:${correct ? "#e6f9e6" : "#fde8e8"};">
                    Your answer: <strong>${userAnswer}</strong> ${correct ? "✅" : "❌"}
                </div>`;
            if (!correct) {
                review += `
                    <div style="padding:6px 10px; margin:4px 0;
                                border-radius:6px; background:#e6f9e6;">
                        Correct answer: <strong>${q.answer}</strong> ✅
                    </div>`;
            }
        }

        review += `</div>`;
    });

    // Show results screen
    document.getElementById("quiz-questions").style.display = "none";
    document.getElementById("quiz-results").style.display   = "block";

    let percent = Math.round((score / quizData.length) * 100);

    document.getElementById("score-display").innerText = `${score} / ${quizData.length}`;

    let message = percent >= 80 ? "🎉 Excellent work!" :
                  percent >= 50 ? "👍 Good effort, keep going!" :
                                  "📚 Review the material and try again!";

    document.getElementById("score-message").innerText  = message;
    document.getElementById("answers-review").innerHTML = review;
}

function retakeQuiz() {
    document.getElementById("quiz-setup").style.display    = "block";
    document.getElementById("quiz-questions").style.display = "none";
    document.getElementById("quiz-results").style.display   = "none";
    document.getElementById("quiz-topic").value = "";
}

async function checkStudyResult() {
    if (!currentStudySessionId) return;
    try {
        let res = await fetch(`${API_URL}/session-result/${currentStudySessionId}`,{
            headers: {
                "Authorization": `Bearer ${getToken()}`
            }
        });
        let data = await res.json();
        if (data.message) {
            showTutorSuggestion(data.message, data.action);
        }
    } catch (err) {
        console.log(err);
    }
}

function showTutorSuggestion(message, action) {
    let box = document.createElement("div");
    box.className = "tutor-popup";

    // If drowsy — show game options instead of generic popup
    if (action === "break" || currentEmotion === "drowsy") {
        box.innerHTML = `
            <p>😴 You seem drowsy! Wake up your brain with a game!</p>
            <div style="display:flex; flex-direction:column; gap:8px; margin-top:10px;">
                <button onclick="launchGame('hangman'); this.closest('.tutor-popup').remove()"
                    style="padding:8px; background:#2563eb; color:white;
                           border:none; border-radius:8px; cursor:pointer;">
                    🔤 Play Hangman
                </button>
                <button onclick="launchGame('crossword'); this.closest('.tutor-popup').remove()"
                    style="padding:8px; background:#1B6CA8; color:white;
                           border:none; border-radius:8px; cursor:pointer;">
                    ✏️ Play Crossword
                </button>
                <button onclick="this.closest('.tutor-popup').remove()"
                    style="padding:8px; background:#eee; border:none;
                           border-radius:8px; cursor:pointer; color:#555;">
                    I'm fine, continue
                </button>
            </div>
        `;
    } else {
        box.innerHTML = `
            <p>${message}</p>
            <div>
                <button onclick="handleTutorAction('${action}')">Yes</button>
                <button onclick="this.closest('.tutor-popup').remove()">Later</button>
            </div>
        `;
    }

    document.body.appendChild(box);
}

function handleTutorAction(action) {

    document.querySelectorAll(".tutor-popup").forEach(e => e.remove());

    if (action === "quiz") {
        startQuickQuiz();
    }
    else if (action === "simplify") {
        document.getElementById("user-input").value =
            "Can you explain that in simpler words?";
        sendMessage();
    }
    else if (action === "break") {
        addMessage("☕ Take a short break. Come back when ready.", "bot");
    }
    else {
        addMessage("How else can I help you?", "bot");
    }
}

setInterval(() => {
    detectEmotionFromCamera();
}, 2000);

navigator.mediaDevices.getUserMedia({ video: true })
.then(stream => {
    document.getElementById("video").srcObject = stream;
})
.catch(err => console.log(err));

async function startQuickQuiz() {

    if (!currentSessionId) {

        alert(
            "No active learning session."
        );

        return;
    }

    try {

        // ---------------------------------------------
        // Get current session topics
        // ---------------------------------------------

        const response =
            await fetch(
                `${API_URL}/session/${currentSessionId}/topics`,
                {
                    headers: {
                        "Authorization":
                            `Bearer ${getToken()}`
                    }
                }
            );

        if (!response.ok) {

            throw new Error(
                "Could not load current topic."
            );
        }

        const data =
            await response.json();

        // ---------------------------------------------
        // Find current topic
        // ---------------------------------------------

        const currentTopic =
            data.topics?.find(
                topic => topic.is_current
            );

        if (!currentTopic) {

            alert(
                "You haven't started learning a topic yet."
            );

            return;
        }

        console.log(
            "Starting quick quiz on:",
            currentTopic.topic
        );

        // ---------------------------------------------
        // Generate quiz directly
        // ---------------------------------------------

        document.getElementById(
            "quiz-modal"
        ).style.display = "flex";

        document.getElementById(
            "quiz-setup"
        ).style.display = "none";

        document.getElementById(
            "quiz-questions"
        ).style.display = "none";

        document.getElementById(
            "quiz-results"
        ).style.display = "none";

        document.getElementById(
            "quiz-loading"
        ).style.display = "block";

        const quizResponse =
            await fetch(
                `${API_URL}/generate-quiz`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Authorization":
                            `Bearer ${getToken()}`
                    },

                    body: JSON.stringify({

                        topic_id:
                            currentTopic.id,

                        session_id:
                            currentSessionId,

                        topic: null,

                        quiz_type: "mcq",

                        num_questions: 5,

                        use_pdf:
                            currentPdfId !== null
                    })
                }
            );

        if (!quizResponse.ok) {

            const errorText =
                await quizResponse.text();

            throw new Error(
                errorText
            );
        }

        const quizResult =
            await quizResponse.json();

        console.log(
            "QUICK QUIZ:",
            quizResult
        );

        quizData =
            quizResult.quiz || [];

        if (
            !quizData ||
            quizData.length === 0
        ) {

            alert(
                "Could not generate the quiz."
            );

            return;
        }

        renderQuiz(
            quizResult.topic ||
            currentTopic.topic,
            "mcq"
        );

    } catch (error) {

        console.error(
            "Quick quiz error:",
            error
        );

        alert(
            "❌ Could not start quiz."
        );

    } finally {

        document.getElementById(
            "quiz-loading"
        ).style.display = "none";
    }
}

// ========== GAME SYSTEM ==========

let hangmanWords    = [];
let hangmanIndex    = 0;
let hangmanWord     = "";
let hangmanGuessed  = [];
let hangmanWrong    = [];
let hangmanMaxWrong = 6;

let crosswordWords  = [];
let crosswordGrid   = [];
let crosswordCells  = {};

// ── Drowsy trigger ────────────────────────────────────────────
function triggerDrowsyGame() {
    document.getElementById("drowsy-popup").style.display = "block";
}

// ── Launch selected game ──────────────────────────────────────
async function launchGame(type) {

    document.getElementById("drowsy-popup").style.display = "none";

    if (!currentSessionId) {
        alert("No active learning session.");
        return;
    }

    try {

        // Get stored learning topics for this session
        const response = await fetch(
            `${API_URL}/session/${currentSessionId}/topics`,
            {
                headers: {
                    "Authorization": `Bearer ${getToken()}`
                }
            }
        );

        if (!response.ok) {
            throw new Error("Could not load learning topics.");
        }

        const data = await response.json();

        // Find the topic currently being studied
        const currentTopic = data.topics?.find(
            topic => topic.is_current
        );

        if (!currentTopic) {

            alert(
                "You haven't started learning a topic yet."
            );

            return;
        }

        console.log(
            "Launching game:",
            type,
            "Topic:",
            currentTopic.topic,
            "Topic ID:",
            currentTopic.id
        );

        // -------------------------------------------------
        // HANGMAN
        // -------------------------------------------------

        if (type === "hangman") {

            document.getElementById(
                "hangman-modal"
            ).style.display = "flex";

            await loadHangmanWords(
                currentTopic.topic,
                currentTopic.id
            );
        }

        // -------------------------------------------------
        // CROSSWORD
        // -------------------------------------------------

        else if (type === "crossword") {

            document.getElementById(
                "crossword-modal"
            ).style.display = "flex";

            await loadCrosswordWords(
                currentTopic.topic,
                currentTopic.id
            );
        }

    } catch (error) {

        console.error(
            "Failed to launch game:",
            error
        );

        alert(
            "❌ Could not start the game."
        );
    }
}

function closeGame(type) {
    document.getElementById(`${type}-modal`).style.display = "none";
}

// ══════════════════════════════════════════════════════════════
// HANGMAN
// ══════════════════════════════════════════════════════════════

async function loadHangmanWords(topic, topicId) {

    document.getElementById(
        "hangman-status"
    ).innerText = "⏳ Loading words...";

    document.getElementById(
        "hangman-word"
    ).innerText = "";

    document.getElementById(
        "hangman-keyboard"
    ).innerHTML = "";

    document.getElementById(
        "hangman-wrong"
    ).innerText = "";

    try {

        const res = await fetch(
            `${API_URL}/generate-hangman`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${getToken()}`
                },

                body: JSON.stringify({

                    topic: null,

                    session_id:
                        currentSessionId,

                    topic_id:
                        topicId,

                    use_pdf: true,

                    num_words: 5
                })
            }
        );

        if (!res.ok) {

            const errorText =
                await res.text();

            throw new Error(
                `HTTP ${res.status}: ${errorText}`
            );
        }

        const data =
            await res.json();

        console.log(
            "HANGMAN RESPONSE:",
            data
        );

        hangmanWords =
            data.words || [];

        hangmanIndex = 0;

        if (
            hangmanWords.length === 0
        ) {

            document.getElementById(
                "hangman-status"
            ).innerText =
                "❌ Could not load words.";

            return;
        }

        // Show topic to student
        document.getElementById(
            "hangman-status"
        ).innerText =
            `📚 Topic: ${data.topic}`;

        startHangmanWord();

    } catch (e) {

        console.error(
            "Hangman error:",
            e
        );

        document.getElementById(
            "hangman-status"
        ).innerText =
            "❌ Error loading words.";
    }
}

function startHangmanWord() {
    let wordObj     = hangmanWords[hangmanIndex];
    hangmanWord     = wordObj.word.toUpperCase();
    hangmanGuessed  = [];
    hangmanWrong    = [];

    document.getElementById("hangman-hint").innerText   = `💡 Hint: ${wordObj.hint}`;
    document.getElementById("hangman-status").innerText = "";
    document.getElementById("hangman-next").style.display = "none";
    document.getElementById("hangman-wrong").innerText  = "";

    drawHangman(0);
    renderHangmanWord();
    renderHangmanKeyboard();
}

function renderHangmanWord() {
    let display = hangmanWord.split("").map(l =>
        hangmanGuessed.includes(l) ? l : "_"
    ).join("  ");
    document.getElementById("hangman-word").innerText = display;
}

function renderHangmanKeyboard() {
    let keyboard = document.getElementById("hangman-keyboard");
    keyboard.innerHTML = "";

    "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").forEach(letter => {
        let btn = document.createElement("button");
        btn.innerText = letter;
        btn.style.cssText = `
            width:36px; height:36px; border:1px solid #ddd;
            border-radius:6px; cursor:pointer; font-size:13px;
            font-weight:bold; background:white;
            transition: all 0.2s;
        `;

        if (hangmanGuessed.includes(letter) || hangmanWrong.includes(letter)) {
            btn.disabled = true;
            btn.style.background = hangmanWrong.includes(letter) ? "#fde8e8" : "#e6f9e6";
            btn.style.color      = hangmanWrong.includes(letter) ? "#f44336" : "#4CAF50";
        }

        btn.addEventListener("click", () => guessHangmanLetter(letter));
        keyboard.appendChild(btn);
    });
}

function guessHangmanLetter(letter) {
    if (hangmanGuessed.includes(letter) || hangmanWrong.includes(letter)) return;

    if (hangmanWord.includes(letter)) {
        hangmanGuessed.push(letter);
    } else {
        hangmanWrong.push(letter);
    }

    drawHangman(hangmanWrong.length);
    renderHangmanWord();
    renderHangmanKeyboard();
    document.getElementById("hangman-wrong").innerText = hangmanWrong.join("  ");

    // Check win
    let allGuessed = hangmanWord.split("").every(l => hangmanGuessed.includes(l));
    if (allGuessed) {
        document.getElementById("hangman-status").innerText = "🎉 Correct! Well done!";
        document.getElementById("hangman-status").style.color = "#4CAF50";
        document.getElementById("hangman-next").style.display = "inline-block";
        return;
    }

    // Check loss
    if (hangmanWrong.length >= hangmanMaxWrong) {
        document.getElementById("hangman-status").innerText =
            `❌ The word was: ${hangmanWord}`;
        document.getElementById("hangman-status").style.color = "#f44336";
        document.getElementById("hangman-next").style.display = "inline-block";
        // Disable all keys
        document.querySelectorAll("#hangman-keyboard button").forEach(b => b.disabled = true);
    }
}

function nextHangmanWord() {
    hangmanIndex++;
    if (hangmanIndex >= hangmanWords.length) {
        document.getElementById("hangman-status").innerText = "🏆 You completed all words!";
        document.getElementById("hangman-next").style.display = "none";
        document.getElementById("hangman-keyboard").innerHTML = "";
        document.getElementById("hangman-word").innerText = "";
        return;
    }
    startHangmanWord();
}

// ── Hangman Drawing ───────────────────────────────────────────
function drawHangman(wrong) {
    let canvas = document.getElementById("hangman-canvas");
    let ctx    = canvas.getContext("2d");
    ctx.clearRect(0, 0, 200, 200);
    ctx.strokeStyle = "#2E4057";
    ctx.lineWidth   = 3;
    ctx.lineCap     = "round";

    // Gallows
    ctx.beginPath();
    ctx.moveTo(20, 190); ctx.lineTo(180, 190); // base
    ctx.moveTo(60, 190); ctx.lineTo(60, 20);   // pole
    ctx.moveTo(60, 20);  ctx.lineTo(130, 20);  // top
    ctx.moveTo(130, 20); ctx.lineTo(130, 45);  // rope
    ctx.stroke();

    if (wrong < 1) return;
    // Head
    ctx.beginPath();
    ctx.arc(130, 60, 15, 0, Math.PI * 2);
    ctx.stroke();

    if (wrong < 2) return;
    // Body
    ctx.beginPath();
    ctx.moveTo(130, 75); ctx.lineTo(130, 130);
    ctx.stroke();

    if (wrong < 3) return;
    // Left arm
    ctx.beginPath();
    ctx.moveTo(130, 90); ctx.lineTo(105, 115);
    ctx.stroke();

    if (wrong < 4) return;
    // Right arm
    ctx.beginPath();
    ctx.moveTo(130, 90); ctx.lineTo(155, 115);
    ctx.stroke();

    if (wrong < 5) return;
    // Left leg
    ctx.beginPath();
    ctx.moveTo(130, 130); ctx.lineTo(105, 160);
    ctx.stroke();

    if (wrong < 6) return;
    // Right leg
    ctx.beginPath();
    ctx.moveTo(130, 130); ctx.lineTo(155, 160);
    ctx.stroke();
}

// ══════════════════════════════════════════════════════════════
// CROSSWORD
// ══════════════════════════════════════════════════════════════

const GRID_SIZE = 15;

async function loadCrosswordWords(topic, topicId) {

    document.getElementById(
        "crossword-grid"
    ).innerHTML =
        "⏳ Generating crossword...";

    document.getElementById(
        "crossword-across"
    ).innerHTML = "";

    document.getElementById(
        "crossword-down"
    ).innerHTML = "";

    document.getElementById(
        "crossword-result"
    ).innerText = "";

    try {

        const res = await fetch(
            `${API_URL}/generate-crossword`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${getToken()}`
                },

                body: JSON.stringify({

                    topic: null,

                    session_id:
                        currentSessionId,

                    topic_id:
                        topicId,

                    use_pdf: true,

                    num_words: 6
                })
            }
        );

        if (!res.ok) {

            const errorText =
                await res.text();

            throw new Error(
                `HTTP ${res.status}: ${errorText}`
            );
        }

        const data =
            await res.json();

        console.log(
            "CROSSWORD RESPONSE:",
            data
        );

        crosswordWords =
            data.words || [];

        if (
            crosswordWords.length === 0
        ) {

            document.getElementById(
                "crossword-grid"
            ).innerHTML =
                "❌ Could not generate crossword.";

            return;
        }

        buildCrossword();

    } catch (e) {

        console.error(
            "Crossword error:",
            e
        );

        document.getElementById(
            "crossword-grid"
        ).innerHTML =
            "❌ Error loading crossword.";
    }
}

function buildCrossword() {
    // Init empty grid
    crosswordGrid = Array(GRID_SIZE).fill(null).map(() => Array(GRID_SIZE).fill(null));
    crosswordCells = {};

    let placed  = [];
    let across  = [];
    let down    = [];
    let clueNum = 1;

    crosswordWords.forEach((item, idx) => {
        let word = item.word.toUpperCase();
        let placed_word = false;

        if (placed.length === 0) {
            // Place first word horizontally in center
            let row = Math.floor(GRID_SIZE / 2);
            let col = Math.floor((GRID_SIZE - word.length) / 2);
            placeWord(word, row, col, "across");
            across.push({ num: clueNum, clue: item.clue, word });
            placed.push({ word, row, col, dir: "across" });
            clueNum++;
            placed_word = true;

        } else {
            // Try to intersect with already placed words
            for (let p of placed) {
                for (let pi = 0; pi < p.word.length; pi++) {
                    for (let wi = 0; wi < word.length; wi++) {
                        if (p.word[pi] !== word[wi]) continue;

                        let row, col, dir;

                        if (p.dir === "across") {
                            // Place new word down
                            row = p.row - wi;
                            col = p.col + pi;
                            dir = "down";
                        } else {
                            // Place new word across
                            row = p.row + pi;
                            col = p.col - wi;
                            dir = "across";
                        }

                        if (canPlace(word, row, col, dir)) {
                            placeWord(word, row, col, dir);
                            if (dir === "across") {
                                across.push({ num: clueNum, clue: item.clue, word });
                            } else {
                                down.push({ num: clueNum, clue: item.clue, word });
                            }
                            placed.push({ word, row, col, dir });
                            clueNum++;
                            placed_word = true;
                            break;
                        }
                    }
                    if (placed_word) break;
                }
                if (placed_word) break;
            }

            // If couldn't intersect, place independently
            if (!placed_word) {
                for (let r = 2; r < GRID_SIZE - 2; r++) {
                    for (let c = 2; c < GRID_SIZE - word.length - 1; c++) {
                        if (canPlace(word, r, c, "across")) {
                            placeWord(word, r, c, "across");
                            across.push({ num: clueNum, clue: item.clue, word });
                            placed.push({ word, row: r, col: c, dir: "across" });
                            clueNum++;
                            placed_word = true;
                            break;
                        }
                    }
                    if (placed_word) break;
                }
            }
        }
    });

    renderCrosswordGrid(placed, across, down);
}

function canPlace(word, row, col, dir) {
    for (let i = 0; i < word.length; i++) {
        let r = dir === "down"   ? row + i : row;
        let c = dir === "across" ? col + i : col;

        if (r < 0 || r >= GRID_SIZE || c < 0 || c >= GRID_SIZE) return false;

        let cell = crosswordGrid[r][c];
        if (cell !== null && cell !== word[i]) return false;
    }
    return true;
}

function placeWord(word, row, col, dir) {
    for (let i = 0; i < word.length; i++) {
        let r = dir === "down"   ? row + i : row;
        let c = dir === "across" ? col + i : col;
        crosswordGrid[r][c] = word[i];
    }
}

function renderCrosswordGrid(placed, across, down) {
    // Find bounding box
    let minR = GRID_SIZE, maxR = 0, minC = GRID_SIZE, maxC = 0;
    for (let r = 0; r < GRID_SIZE; r++) {
        for (let c = 0; c < GRID_SIZE; c++) {
            if (crosswordGrid[r][c] !== null) {
                minR = Math.min(minR, r);
                maxR = Math.max(maxR, r);
                minC = Math.min(minC, c);
                maxC = Math.max(maxC, c);
            }
        }
    }

    // Clue numbers map
    let clueNums = {};
    [...across, ...down].forEach(item => {
        placed.forEach(p => {
            if (p.word === item.word) {
                let key = `${p.row},${p.col}`;
                clueNums[key] = item.num;
            }
        });
    });

    let table = document.createElement("table");
    table.style.cssText = "border-collapse:collapse; margin:0 auto;";

    crosswordCells = {};

    for (let r = minR; r <= maxR; r++) {
        let tr = document.createElement("tr");
        for (let c = minC; c <= maxC; c++) {
            let td = document.createElement("td");
            td.style.cssText = `
                width:34px; height:34px; border:1px solid #ccc;
                position:relative; padding:0;
                background: ${crosswordGrid[r][c] !== null ? "white" : "#2E4057"};
            `;

            if (crosswordGrid[r][c] !== null) {
                // Clue number label
                let key = `${r},${c}`;
                if (clueNums[key]) {
                    let num = document.createElement("span");
                    num.innerText = clueNums[key];
                    num.style.cssText = `
                        position:absolute; top:1px; left:2px;
                        font-size:9px; color:#666; line-height:1;
                    `;
                    td.appendChild(num);
                }

                // Input cell
                let input = document.createElement("input");
                input.maxLength = 1;
                input.dataset.answer = crosswordGrid[r][c];
                input.style.cssText = `
                    width:100%; height:100%; border:none; outline:none;
                    text-align:center; font-size:16px; font-weight:bold;
                    text-transform:uppercase; background:transparent;
                    cursor:pointer; caret-color:#2563eb;
                `;
                input.addEventListener("input", () => {
                    input.value = input.value.toUpperCase().slice(-1);
                });
                td.appendChild(input);
                crosswordCells[`${r},${c}`] = input;
            }

            tr.appendChild(td);
        }
        table.appendChild(tr);
    }

    document.getElementById("crossword-grid").innerHTML = "";
    document.getElementById("crossword-grid").appendChild(table);

    // Render clues
    let acrossDiv = document.getElementById("crossword-across");
    let downDiv   = document.getElementById("crossword-down");

    acrossDiv.innerHTML = across.map(a =>
        `<p style="font-size:13px; margin:4px 0;">
            <strong>${a.num}.</strong> ${a.clue}
        </p>`
    ).join("");

    downDiv.innerHTML = down.map(d =>
        `<p style="font-size:13px; margin:4px 0;">
            <strong>${d.num}.</strong> ${d.clue}
        </p>`
    ).join("");
}

function checkCrossword() {
    let total   = 0;
    let correct = 0;

    Object.entries(crosswordCells).forEach(([key, input]) => {
        total++;
        let userVal = input.value.toUpperCase();
        let answer  = input.dataset.answer;

        if (userVal === answer) {
            correct++;
            input.style.color      = "#4CAF50";
            input.style.background = "#e6f9e6";
        } else {
            input.style.color      = "#f44336";
            input.style.background = "#fde8e8";
        }
    });

    let percent = Math.round((correct / total) * 100);
    let msg     = percent === 100 ? "🎉 Perfect! All correct!" :
                  percent >= 60   ? `👍 ${correct}/${total} correct! Keep going!` :
                                    `📚 ${correct}/${total} correct. Try again!`;

    document.getElementById("crossword-result").innerText = msg;
}

function openGamePicker() {
    // Reuse the same showTutorSuggestion game popup
    if (!document.querySelector(".tutor-popup")) {
        showTutorSuggestion("drowsy", "break");
    } else {
        // If already open, remove and reopen
        document.querySelectorAll(".tutor-popup").forEach(e => e.remove());
        showTutorSuggestion("drowsy", "break");
    }
}

// ⬇ Export the conversation as a text file
function downloadChat(){
    let text=document.getElementById("chat-box").innerText;
    let blob=new Blob([text],{type:"text/plain"});
    let a=document.createElement("a");
    a.href=URL.createObjectURL(blob);
    a.download="StudySession.txt";
    a.click();
}

// 🗑 Reset the chat back to the welcome screen
function clearChat(){
    document.getElementById("chat-box").innerHTML=`
    <div class="welcome">
        <h2>Hello! I'm your AI Tutor</h2>
        <p>I detect how you're feeling and adapt explanations.</p>
    </div>
    `;
}

function openSessions() {
    const chatBox = document.getElementById("chat-box");
    chatBox.scrollTop = chatBox.scrollHeight;
}

function toggleTheme() {
    document.body.classList.toggle("dark-mode");
}

function logoutUser() {
    if (!confirm("Do you want to logout?"))
        return;
    localStorage.removeItem("token");
    localStorage.removeItem("name");
    localStorage.removeItem("lastSession");
    clearChat();
    window.location.href = "login.html";
}

async function openSession(sessionId) {

    try {

        currentSessionId = sessionId;

        localStorage.setItem(
            "lastSession",
            sessionId
        );

        const response = await fetch(
            `${API_URL}/session/${sessionId}`,
            {
                headers: {
                    Authorization:
                        `Bearer ${getToken()}`
                }
            }
        );

        if (!response.ok) {
            throw new Error(
                "Failed to load session"
            );
        }

        const data = await response.json();

        // ---------------------------------------------
        // Restore PDF attached to this conversation
        // ---------------------------------------------

        if (data.pdf) {

            currentPdfId = data.pdf.id;

            console.log(
                "Session PDF:",
                data.pdf.filename
            );

        } else {

            currentPdfId = null;
        }

        // ---------------------------------------------
        // Restore messages
        // ---------------------------------------------

        const chatBox =
            document.getElementById(
                "chat-box"
            );

        chatBox.innerHTML = "";

        const messages =
            data.messages || [];

        messages.forEach(chat => {

            addMessage(
                chat.question,
                "user"
            );

            const id =
                addTypingIndicator();

            updateMessage(
                id,
                chat.answer,
                chat.answer
            );
        });

        chatBox.scrollTop =
            chatBox.scrollHeight;

        console.log(
            "Opened session:",
            sessionId,
            "PDF:",
            currentPdfId
        );

    } catch (error) {

        console.error(
            "Failed to open session:",
            error
        );

        alert(
            "Could not load this conversation."
        );
    }
}


async function deleteSession(sessionId, event) {
    event.stopPropagation();
    if (!confirm("Delete this chat?"))
        return;
    await fetch(`${API_URL}/session/${sessionId}`, {
        method: "DELETE",
        headers: {
            Authorization: `Bearer ${getToken()}`
        }
    });

    if (currentSessionId == sessionId) {
        currentSessionId = null;
        localStorage.removeItem("lastSession");
        clearChat();
    }
    loadSessions();
}

async function searchChats(){
    let keyword = document
        .getElementById("search-chat")
        .value
        .trim();
    if(keyword===""){
        loadSessions();
        return;
    }
    const res = await fetch(
        `${API_URL}/session/search/${keyword}`,
        {
            headers:{
                Authorization:`Bearer ${getToken()}`
            }
        }
    );
    const sessions = await res.json();
    const container = document.getElementById("sessions-container");
    container.innerHTML="";
    sessions.forEach(session=>{
        container.innerHTML += `
            <div class="session-item"
                 onclick="openSession(${session.id})">
                <strong>${session.title}</strong><br>
                <small>${session.created_at}</small>
            </div>
        `;
    });
}

async function generateNotes() {
    if (!currentSessionId) {
        alert("No chat available.");
        return;
    }
    try {
        let res = await fetch(
            `${API_URL}/notes/${currentSessionId}`,
            {
                headers: {
                    Authorization: `Bearer ${getToken()}`
                }
            }
        );
        let data = await res.json();
        console.log(data.notes);
        showNotesModal(data.notes);
    } catch (err) {
        console.log(err);
    }
}

function showNotesModal(notes) {
    document.getElementById("notes-content").innerHTML =
        marked.parse(notes);
    document.getElementById("notes-modal").style.display = "flex";
}

function closeNotesModal() {
    document.getElementById("notes-modal").style.display = "none";
}

async function downloadNotesPDF() {
    const { jsPDF } = window.jspdf;
    const element = document.getElementById("notes-content");
    const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true
    });
    const imgData = canvas.toDataURL("image/png");
    const pdf = new jsPDF("p", "mm", "a4");
    const pageWidth = 210;
    const pageHeight = 297;
    const imgWidth = pageWidth;
    const imgHeight = canvas.height * imgWidth / canvas.width;
    let heightLeft = imgHeight;
    let position = 0;
    pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;
    while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(
            imgData,
            "PNG",
            0,
            position,
            imgWidth,
            imgHeight
        );
        heightLeft -= pageHeight;
    }
    pdf.save("Study_Notes.pdf");
}

async function loadPDFs() {
    const res = await fetch(`${API_URL}/pdfs`, {
        headers: {
            Authorization: `Bearer ${getToken()}`
        }
    });
    const pdfs = await res.json();
    const container = document.getElementById("pdf-list");
    container.innerHTML = "";
    pdfs.forEach(pdf => {
        container.innerHTML += `
            <div class="pdf-item"
                 onclick="selectPDF(${pdf.id}, '${pdf.filename}')">
                📄 ${pdf.filename}
            </div>
        `;
    });
}

async function selectPDF(id, filename) {

    console.log(
        "Selecting PDF:",
        id,
        filename
    );

    try {

        // Create a NEW conversation attached to this PDF
        await createNewSession(id);

        console.log(
            "PDF chat session created:",
            currentSessionId
        );

        alert(
            `📄 ${filename} selected`
        );

    } catch (error) {

        console.error(
            "Failed to select PDF:",
            error
        );

        alert(
            "Could not open PDF chat."
        );
    }
}