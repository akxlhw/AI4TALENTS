"""CS related discipline Concept IDs from OpenAlex.

These concept IDs are used to calculate CS background score for authors,
helping filter non-CS/AI background talents from the database.

OpenAlex Concepts: https://openalex.org/topics
"""

# Core CS concepts for calculating CS background score
# Format: OpenAlex Concept ID (without https://openalex.org/ prefix)
CORE_CS_CONCEPTS = {
    # Level 0 - Top level
    "C41008148",  # Computer Science

    # Level 1 - Core disciplines
    "C154945302",  # Artificial Intelligence
    "C119857082",  # Machine Learning
    "C31972630",   # Computer Vision
    "C204321447",  # Natural Language Processing
    "C124101348",  # Data Mining
    "C2522767166", # Data Science
    "C77088390",   # Database
    "C31258907",   # Computer Network
    "C115903868",  # Software Engineering
    "C111919701",  # Operating System
    "C120314980",  # Distributed Computing
    "C199360897",  # Programming Language
    "C76155785",   # Telecommunications
    "C527648132",  # Information Security

    # Level 2 - Secondary disciplines
    "C90509273",   # Robot
    "C34413123",   # Robotics
    "C19966478",   # Mobile Robot
    "C110875604",  # The Internet
}

# Threshold for filtering non-CS background authors
# Authors with CS score below this threshold will not be synced to Talent
# Set to 0.3 to allow some cross-disciplinary work while filtering clearly non-CS authors
CS_SCORE_THRESHOLD = 0.3
