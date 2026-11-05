# Insurance Assistant

A standalone insurance assistant application with customer registration/login, a one-question-at-a-time insurance needs questionnaire, and a hybrid FAQ + optional OpenAI chatbot.

## Features
- Customer registration and login with password hashing.
- Personalized greeting using the customer's registered name.
- Guided onboarding: age, insurance type, budget period and amount, desired coverage, and existing policy.
- Saves each answer to the signed-in customer's insurance profile.
- Customer-specific chat history.
- FAQ matching first; OpenAI response if no FAQ matches; fallback if AI is unavailable.
- Profile page to review saved answers.
- SQLite for a simple first run; MySQL supported through DATABASE_URL.

## Windows setup
1. Extract the ZIP and open this folder in VS Code.
2. Open Terminal > New Terminal (PowerShell).
3. Create virtual environment:

   ```powershell
   py -3 -m venv .venv
   ```
4. Activate it:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
   .\.venv\Scripts\Activate.ps1
   ```

   If activation is blocked, use `\.venv\Scripts\python.exe` instead of `python` in the following commands.
5. Install packages:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```
6. Copy environment template:

   ```powershell
   Copy-Item .env.example .env
   ```
7. Open `.env`. Change `SECRET_KEY`. For first run keep SQLite:

   ```env
   DATABASE_URL=sqlite:///insurance_assistant.db
   OPENAI_API_KEY=
   OPENAI_MODEL=gpt-4o-mini
   ```

8. Initialize database and FAQ records:

   ```powershell
   python -m flask --app app init-db
   ```
9. Run application:

   ```powershell
   python -m flask --app app run --debug
   ```
10. Open http://127.0.0.1:5000 and create an account.

## Enable AI
Set your API key in `.env` on the backend only:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

Restart Flask. The chatbot searches FAQs first and calls the AI model only if no FAQ answer is found. API usage may incur charges. Never put the key in HTML or JavaScript.

## Optional MySQL configuration
Create a separate database and application user in MySQL Workbench:

```sql
CREATE DATABASE IF NOT EXISTS insurance_assistant
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'insurance_app'@'localhost' IDENTIFIED BY 'ChooseYourOwnStrongPassword';
GRANT ALL PRIVILEGES ON insurance_assistant.* TO 'insurance_app'@'localhost';
FLUSH PRIVILEGES;
```

Then change DATABASE_URL in `.env`:

```env
DATABASE_URL=mysql+pymysql://insurance_app:YOUR_PASSWORD@127.0.0.1:3306/insurance_assistant?charset=utf8mb4
```

If the password contains URL-special characters, URL-encode them. Run `init-db` after changing the database.

## Important notes
- The questionnaire gathers preferences only. It does not calculate premiums, recommend a specific insurer product, decide eligibility, or issue a quote.
- This is a learning/demo starter, not a production insurance system.
- Do not enter real customer, medical, identity, banking, password, or OTP data.
- Before production, add CSRF protection, email verification, password reset, rate limiting, stronger session controls, audit logs, privacy/retention controls, HTTPS, security tests, and regulatory review.
- AI responses must not be treated as official policy wording or claim decisions.
