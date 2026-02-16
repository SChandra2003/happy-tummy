🍽️ HappyTummy – Food Donation & Distribution Platform

HappyTummy is a web-based platform designed to reduce food wastage by connecting restaurants, NGOs, and volunteers. It enables surplus food donations, efficient coordination, and transparent distribution to those in need.

🌟 Problem Statement

Large quantities of edible food are wasted every day while many people struggle with hunger. There is a lack of a centralized, structured system that connects food donors with organizations and volunteers who can distribute food efficiently.

HappyTummy bridges this gap.

🎯 Objectives

Minimize food wastage from restaurants

Enable NGOs to request and manage food donations

Allow volunteers to participate in food pickup and delivery

Provide role-based dashboards for smooth coordination

Ensure transparency and accountability in food distribution

👥 User Roles
🏪 Restaurant

Register and log in

Submit surplus food details

Track donation status

🏢 NGO

Register and log in

Request food based on availability

Manage received donations

🚴 Volunteer

Register and log in

Accept delivery requests

Assist in food pickup and distribution

🛠️ Tech Stack
Frontend

HTML5

CSS3

Bootstrap 5

JavaScript

Backend

Python

Django Framework

Database

SQLite (Development)

Easily extendable to PostgreSQL / MySQL

Authentication

Django Authentication System

Role-based access control

✨ Key Features

🔐 Secure user authentication

🧩 Role-based dashboards (Restaurant / NGO / Volunteer)

📦 Food surplus submission & confirmation

🔄 Real-time donation workflow

📊 Organized database structure

🌐 Scalable and modular architecture

⚙️ Installation & Setup
1️⃣ Clone the Repository
git clone https://github.com/your-username/HappyTummy.git
cd HappyTummy

2️⃣ Create Virtual Environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Run Migrations
python manage.py makemigrations
python manage.py migrate

5️⃣ Start the Server
python manage.py runserver


LIVE DEPLOYMENT LINK:

🧪 Testing Credentials (Optional)

You can create test users using the registration pages for:

Restaurant

NGO

Volunteer

Or via Django Admin:

python manage.py createsuperuser

🚀 Future Enhancements

📍 Google Maps integration for live tracking

📱 Mobile app version

🔔 Notification system (SMS / Email)

☁️ Cloud database deployment

📈 Analytics dashboard for impact measurement

🤝 Contribution

Contributions are welcome!
Feel free to fork the repository and submit a pull request.

📜 License

This project is developed for educational purposes and is open for learning and improvement.

❤️ Acknowledgement

HappyTummy is inspired by the vision of creating a hunger-free society by leveraging technology for social good.
