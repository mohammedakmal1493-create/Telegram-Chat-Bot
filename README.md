Markdown


# Telegram Canteen Automation Bot

A lightweight, state-driven Telegram bot designed to automate food ordering, menu distribution, and secure counter pickup verification for educational institutes or corporate canteens. Built using Python, the `pyTelegramBotAPI` framework, and an embedded SQLite database layout.

---

## 🛠️ Features

* **State-Driven Multi-Step Ordering:** Tracks user workflows smoothly across conversational milestones (Menu View $\rightarrow$ Item Selection $\rightarrow$ Confirmation $\rightarrow$ Pickup Ready).
* **Automated Pickup Verification:** Generates a localized unique alphanumeric verification string and matching JSON-embedded QR Code upon order confirmation.
* **Embedded Database Architecture:** Utilizes SQLite to manage persistent transactional histories, data tables (Menu, Orders, Sessions), and row updates.
* **Inline Administrative Suite:** Provides a permissioned command matrix for campus canteen staff to dynamically manipulate the active food registry via text commands.
* **JSON-In-DB Serialization:** Preserves item lists and bulk item quantifiers cleanly inside single database rows using structured JSON stringification.

---

## 📂 Project Architecture

```text
smartcanteenbot/
│
├── .env                  # Configuration variables (Secret tokens & Admin lists)
├── app.py                # Core conversational router and event handler
├── db_manager.py         # Relational schema boundaries and database CRUD actions
│
├── simple_canteen_bot.db # Created automatically on execution (SQLite DB)
└── static/               # Created automatically on execution (Stores active QR images)
⚙️ Setup and Installation
1. Prerequisite Installations
Ensure your development environment contains Python 3.10+ installed. Install the explicit dependencies using pip:

Bash


pip install pyTelegramBotAPI python-dotenv qrcode pillow
2. Register Your Bot
Search for @BotFather on Telegram.

Initialize with /newbot and follow the structural naming wizard.

Secure your generated HTTP API Bot Token.

3. Identify Admin Chat IDs
Canteen staff require explicit command permissions. Find your numeric unique chat signature by messaging @userinfobot on Telegram.

4. Configure Environment Variables
Create a file named .env in the root directories of the project mapping your credentials:

Code snippet


BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
ADMIN_CHAT_IDS=987654321,555444333
(Separate multiple administrative personnel signatures using commas).

🚀 Execution
Initialize the backend wrapper by booting your primary runtime entry file:

Bash


python app.py
Upon verification, the system creates the database mappings, feeds initial preset tokens (Samosa, Tea, Coffee, Vada Pav), flushes active webhooks to bypass error 409 boundaries, and opens long-polling pipelines.

📋 Operational Workflow
Student User Flow
Initiate: Student messages menu, hi, or /start.

Select: User targets key codes using format: <item_id> <quantity> (e.g., replying 1 2 commands two units of ID 1).

Confirm: Bot creates an explicit summary transaction tracking state as pending. Student replies confirm or cancel.

Collect: Bot renders the transaction status to confirmed, notifies management channels, and posts a scannable token for counter processing.

Admin Command Terminal
Users whose Chat IDs reside in your .env register can interact with the bot using administrative shortcuts directly:

admin menu — Audits the total items cataloged inside the relational tracking file.

add <item name> <price> — Extends active selections (e.g., add Cold Coffee 35).

delete <id> — Performs soft-deletions changing row visibility fields to false (available = 0).
