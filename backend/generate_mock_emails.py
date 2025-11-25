import json
from datetime import datetime, timedelta
import random

# Email templates for different categories
templates = {
    "meetings": [
        {
            "sender": "calendar@company.com",
            "subject": "Meeting Invitation: {topic}",
            "body": "You've been invited to a meeting about {topic}.\n\nDate: {date}\nTime: {time}\nLocation: {location}\n\nAgenda:\n{agenda}\n\nPlease confirm your attendance."
        },
        {
            "sender": "team.lead@company.com",
            "subject": "Sync Meeting: {topic}",
            "body": "Hi team,\n\nLet's sync up on {topic}. I've scheduled a meeting for {date} at {time} in {location}.\n\nTopics to cover:\n{agenda}\n\nSee you there!"
        }
    ],
    "work_updates": [
        {
            "sender": "project.manager@company.com",
            "subject": "Project Update: {project}",
            "body": "Status update on {project}:\n\nProgress: {progress}%\nMilestones: {milestone}\nRisks: {risk}\nNext Steps: {next_steps}\n\nPlease review and provide feedback."
        },
        {
            "sender": "engineering@company.com",
            "subject": "{project} - Sprint Review",
            "body": "Sprint {sprint_num} has been completed!\n\nCompleted Items:\n{completed}\n\nCarried Over:\n{carryover}\n\nNext sprint starts {date}."
        }
    ],
    "newsletters": [
        {
            "sender": "newsletter@{domain}.com",
            "subject": "{title} - Weekly Digest",
            "body": "Your weekly roundup of {topic} news:\n\n{content}\n\nTop stories:\n{stories}\n\nTrending: {trending}"
        }
    ],
    "notifications": [
        {
            "sender": "notifications@company.com",
            "subject": "[{system}] {alert}",
            "body": "System: {system}\nStatus: {status}\nTime: {time}\nDetails: {details}\n\nAction required: {action}"
        }
    ],
    "client_emails": [
        {
            "sender": "{client}@client.com",
            "subject": "Re: {topic}",
            "body": "Hi,\n\nThanks for your message about {topic}. {response}\n\n{details}\n\nLooking forward to your response.\n\nBest,\n{name}"
        }
    ],
    "spam": [
        {
            "sender": "promo@{domain}.xyz",
            "subject": "{urgent} {offer}% OFF - {product}",
            "body": "{urgency}\n\n{product} now available at {offer}% discount!\n\n{cta}\n\nClick here now!"
        }
    ]
}

# Data for generating variety
topics = ["Q4 Planning", "Product Roadmap", "Team Sync", "Client Review", "Budget Discussion", 
          "Feature Launch", "Security Update", "Performance Review", "Training Session", "Code Review"]
          
projects = ["Customer Portal", "Mobile App", "API Integration", "Database Migration", "Frontend Redesign",
            "Cloud Infrastructure", "Analytics Dashboard", "Payment System", "User Authentication", "Search Engine"]
            
locations = ["Conference Room A", "Zoom", "Teams", "Main Office", "Remote", "Board Room", "Cafeteria", "Online"]

systems = ["Production", "Staging", "CI/CD", "Database", "API Gateway", "Monitoring", "Backup", "Security"]

domains = ["techcrunch", "hacknews", "devto", "medium", "linkedin", "github", "stackoverflow"]

clients = ["Acme Corp", "TechStart", "GlobalSolutions", "InnovateCo", "DataDynamics", "CloudFirst"]

names = ["John Smith", "Emily Davis", "Michael Chen", "Sarah Johnson", "David Wilson", "Lisa Anderson"]

def generate_timestamp(days_ago):
    """Generate timestamp for emails from past days"""
    base = datetime(2023, 11, 22)
    return (base - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))).isoformat() + "Z"

def generate_email(email_id, category, days_ago):
    """Generate a single email based on category"""
    template = random.choice(templates[category])
    
    # Fill in template variables
    subject = template["subject"]
    body = template["body"]
    sender = template["sender"]
    
    # Replace placeholders with random data
    replacements = {
        "{topic}": random.choice(topics),
        "{project}": random.choice(projects),
        "{date}": f"Nov {random.randint(20, 30)}",
        "{time}": f"{random.randint(9, 17)}:00 {random.choice(['AM', 'PM'])}",
        "{location}": random.choice(locations),
        "{agenda}": f"- {random.choice(topics)}\n- {random.choice(topics)}\n- Q&A",
        "{progress}": str(random.randint(40, 95)),
        "{milestone}": random.choice(["On Track", "At Risk", "Completed", "In Progress"]),
        "{risk}": random.choice(["None", "Minor delays", "Resource constraints", "Dependencies"]),
        "{next_steps}": random.choice(["Continue development", "Testing phase", "Deploy to staging", "Client review"]),
        "{sprint_num}": str(random.randint(10, 25)),
        "{completed}": f"- {random.choice(topics)}\n- {random.choice(topics)}",
        "{carryover}": f"- {random.choice(topics)}",
        "{domain}": random.choice(domains),
        "{title}": random.choice(["Tech Weekly", "Dev Digest", "Industry News", "Product Updates"]),
        "{content}": "Latest developments in technology and industry news.",
        "{stories}": f"1. {random.choice(topics)}\n2. {random.choice(topics)}\n3. {random.choice(topics)}",
        "{trending}": random.choice(topics),
        "{system}": random.choice(systems),
        "{alert}": random.choice(["Alert", "Notification", "Update", "Warning"]),
        "{status}": random.choice(["Success", "Warning", "Error", "Info"]),
        "{details}": "System performing normally. No action required.",
        "{action}": random.choice(["None", "Review logs", "Monitor metrics", "Update config"]),
        "{client}": random.choice(clients).lower().replace(" ", ""),
        "{response}": "I've reviewed your request and have some updates to share.",
        "{name}": random.choice(names),
        "{urgent}": random.choice(["URGENT", "FINAL NOTICE", "LAST CHANCE", "LIMITED TIME"]),
        "{offer}": str(random.randint(50, 90)),
        "{product}": random.choice(["Premium Subscription", "Software Suite", "Cloud Storage", "Security Tools"]),
        "{urgency}": "This offer expires soon!",
        "{cta}": "Don't miss out! Act now!"
    }
    
    for key, value in replacements.items():
        subject = subject.replace(key, value)
        body = body.replace(key, value)
        sender = sender.replace(key, value.lower().replace(" ", ""))
    
    return {
        "id": email_id,
        "sender": sender,
        "subject": subject,
        "body": body,
        "timestamp": generate_timestamp(days_ago)
    }

# Generate 100 emails with variety
emails = []
email_id = 1

# Distribution of email types
distribution = {
    "meetings": 20,
    "work_updates": 25,
    "newsletters": 15,
    "notifications": 20,
    "client_emails": 15,
    "spam": 5
}

for category, count in distribution.items():
    for i in range(count):
        days_ago = random.randint(0, 30)  # Emails from last 30 days
        email = generate_email(email_id, category, days_ago)
        emails.append(email)
        email_id += 1

# Sort by timestamp (most recent first)
emails.sort(key=lambda x: x["timestamp"], reverse=True)

# Reassign IDs after sorting
for idx, email in enumerate(emails, 1):
    email["id"] = idx

# Save to file
with open("mock_inbox.json", "w", encoding="utf-8") as f:
    json.dump(emails, f, indent=2, ensure_ascii=False)

print(f"✅ Generated {len(emails)} mock emails!")
print(f"📊 Distribution:")
for category, count in distribution.items():
    print(f"   - {category}: {count}")
