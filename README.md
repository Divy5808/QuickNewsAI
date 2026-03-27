# 📰 QuickNewsAI

QuickNewsAI is an AI-powered web application that extracts, summarizes, and translates news articles from URLs. It helps users quickly understand news content in multiple languages.

---

## 🚀 Features

* 🔗 Extract news from any URL
* ✂️ AI-based text summarization
* 🌐 Multi-language translation (English, Gujarati, Hindi)
* 📊 User dashboard with history
* 👤 User authentication (Login/Profile)
* 🕘 View previously summarized news

---

## 🛠️ Tech Stack

* **Backend:** Python (Flask)
* **Frontend:** HTML, CSS, Bootstrap
* **Database:** PostgreSQL
* **AI Tools:** NLP models, gTTS (Text-to-Speech)

---

## 📂 Project Structure

```
QuickNewsAI/
│── static/
│── templates/
│── app.py
│── requirements.txt
│── .gitignore
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Divy5808/QuickNewsAI.git
cd QuickNewsAI
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Run Project

```bash
python app.py
```

---

## 🌍 Free Deployment (Hugging Face Spaces)

Hugging Face Spaces is the ideal platform for deploying AI projects using PyTorch and Transformers since it provides up to 16GB of RAM completely free forever. We have included a `Dockerfile` specifically for this.

### Steps to Deploy:
1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) and create a free account.
2. Click on **Create new Space**.
3. Choose a name (e.g., `QuickNewsAI`).
4. For the **Space SDK**, select **Docker** and choose **Blank**.
5. Once created, connect your GitHub repository or upload your files there.
6. Because the `Dockerfile` is already present, Hugging Face will automatically download your models and run the app 24/7 on the internet for free!

---

## 📸 Screenshots

* Dashboard
* News Summary Page
* History Page

---

## 👨‍💻 Author

**Divy Dalwadi**

---

## 📌 Future Improvements

* 🤖 Custom AI model integration
* 📱 Mobile responsive UI improvements
* 🔔 Real-time news updates

---

## ⭐ Support

If you like this project, give it a ⭐ on GitHub!
