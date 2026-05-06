"""
Generate sample student data for existing schools.
"""
import random
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Sample data pools
FIRST_NAMES = [
    "James", "John", "Robert", "Michael", "David", "William", "Richard", "Joseph",
    "Thomas", "Charles", "Daniel", "Matthew", "Anthony", "Mark", "Steven", "Paul",
    "Andrew", "Joshua", "Kenneth", "Kevin", "Brian", "George", "Timothy", "Ronald",
    "Edward", "Jason", "Jeffrey", "Ryan", "Jacob", "Gary", "Nicholas", "Eric",
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica",
    "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra", "Ashley",
    "Kimberly", "Emily", "Donna", "Michelle", "Dorothy", "Carol", "Amanda", "Melissa",
    "Emma", "Olivia", "Sophia", "Isabella", "Mia", "Charlotte", "Amelia", "Harper",
    "Wei", "Ming", "Xiaoming", "Lei", "Yong", "Jie", "Hao", "Yu",
    "Yuki", "Sakura", "Haruto", "Sota", "Yuto", "Kaito", "Ryusei", "Koki",
    "Min-Jun", "Ji-Ho", "Seo-Jun", "Do-Yun", "Si-Woo", "Ji-Hoon", "Ha-Jun", "Jun-Woo",
    "Ananya", "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Reyansh", "Krishna",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Wang", "Li", "Zhang", "Liu", "Chen", "Yang", "Huang", "Zhao", "Wu", "Zhou",
    "Tanaka", "Yamamoto", "Suzuki", "Takahashi", "Watanabe", "Ito", "Kobayashi", "Yoshida",
    "Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho", "Yoon",
    "Patel", "Singh", "Kumar", "Sharma", "Gupta", "Verma", "Agarwal", "Reddy",
]

RESEARCH_TOPICS = [
    "Machine Learning", "Deep Learning", "Computer Vision", "Natural Language Processing",
    "Robotics", "Data Science", "Artificial Intelligence", "Neural Networks",
    "Quantum Computing", "Blockchain", "Cybersecurity", "Cloud Computing",
    "Internet of Things", "Big Data Analytics", "Software Engineering", "Database Systems",
    "Computer Networks", "Operating Systems", "Algorithms", "Computer Architecture",
    "Bioinformatics", "Computational Biology", "Medical Imaging", "Drug Discovery",
    "Materials Science", "Nanotechnology", "Energy Systems", "Climate Science",
    "Physics", "Chemistry", "Mathematics", "Statistics",
    "Economics", "Finance", "Marketing", "Management",
    "Psychology", "Neuroscience", "Cognitive Science", "Education",
]

DEPARTMENTS = [
    "Computer Science", "Electrical Engineering", "Mechanical Engineering",
    "Biological Sciences", "Chemistry", "Physics", "Mathematics",
    "Economics", "Business School", "Medical School",
    "School of Law", "School of Education", "School of Architecture",
]


def generate_student_name():
    """Generate a random student name."""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_research_topics():
    """Generate random research topics (2-4 topics)."""
    count = random.randint(2, 4)
    return random.sample(RESEARCH_TOPICS, min(count, len(RESEARCH_TOPICS)))


def generate_student_data(school_id: int, school_name: str, num_students: int) -> list:
    """Generate student data for a school."""
    students = []

    for _ in range(num_students):
        # Student academic metrics (typically lower than professors)
        works_count = random.randint(0, 15)
        cited_by_count = random.randint(0, works_count * 50)  # Students have fewer citations
        h_index = random.randint(0, min(5, works_count))

        # Academic age (years since first publication)
        academic_age = random.randint(1, 6) if works_count > 0 else 0

        student = {
            "name": generate_student_name(),
            "name_en": None,
            "orcid": None,
            "role_type": "student",
            "role_confidence": random.uniform(0.7, 0.95),
            "school_id": school_id,
            "current_title": random.choice(["PhD Student", "Master's Student", "Research Assistant", "Graduate Student", ""]),
            "works_count": works_count,
            "cited_by_count": cited_by_count,
            "h_index": h_index,
            "latest_active_year": random.randint(2022, 2025),
            "topic_tags": generate_research_topics(),
            "department_name": random.choice(DEPARTMENTS),
            "research_interests": None,
            "summary": None,
            "lab_name": None,
            "visibility_status": "active",
            "is_visible": True,
        }
        students.append(student)

    return students


def main():
    """Generate and insert student data."""
    engine = create_engine('sqlite:///./talent.db')

    with engine.connect() as conn:
        # Get all schools
        result = conn.execute(text('SELECT school_id, school_name FROM core_school'))
        schools = [(row[0], row[1]) for row in result.fetchall()]

        print(f"Found {len(schools)} schools")

        total_students = 0
        for school_id, school_name in schools:
            # Generate 10-30 students per school
            num_students = random.randint(10, 30)
            students = generate_student_data(school_id, school_name, num_students)

            for student in students:
                conn.execute(text('''
                    INSERT INTO core_talent (
                        name, name_en, orcid, role_type, role_confidence,
                        school_id, current_title, works_count, cited_by_count,
                        h_index, latest_active_year, topic_tags, department_name,
                        research_interests, summary, lab_name, visibility_status, is_visible,
                        created_at, updated_at
                    ) VALUES (
                        :name, :name_en, :orcid, :role_type, :role_confidence,
                        :school_id, :current_title, :works_count, :cited_by_count,
                        :h_index, :latest_active_year, :topic_tags, :department_name,
                        :research_interests, :summary, :lab_name, :visibility_status, :is_visible,
                        :created_at, :updated_at
                    )
                '''), {
                    **student,
                    "topic_tags": str(student["topic_tags"]),  # Convert list to string for SQLite
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                })
                total_students += 1

            print(f"  {school_name}: +{num_students} students")

        conn.commit()
        print(f"\nTotal students added: {total_students}")

        # Verify
        result = conn.execute(text('SELECT role_type, COUNT(*) FROM core_talent GROUP BY role_type'))
        print("\nUpdated role distribution:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")


if __name__ == "__main__":
    main()
