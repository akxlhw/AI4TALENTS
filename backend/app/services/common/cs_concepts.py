"""CS related discipline Concept IDs from OpenAlex.

These concept IDs are used to calculate CS background score for authors,
helping filter non-CS/AI background talents from the database.

OpenAlex Concepts: https://openalex.org/topics

Note: OpenAlex x_concepts.id format is pure number string (e.g., "41008148")
"""
import logging

logger = logging.getLogger(__name__)

# Core CS concepts for calculating CS background score
# Format: Pure number string as returned by OpenAlex x_concepts.id
CORE_CS_CONCEPTS = {
    # Level 0 - Top level
    "41008148",  # Computer Science

    # Level 1 - Core disciplines
    "154945302",  # Artificial Intelligence
    "119857082",  # Machine Learning
    "31972630",   # Computer Vision
    "204321447",  # Natural Language Processing
    "124101348",  # Data Mining
    "2522767166", # Data Science
    "77088390",   # Database
    "31258907",   # Computer Network
    "115903868",  # Software Engineering
    "111919701",  # Operating System
    "120314980",  # Distributed Computing
    "199360897",  # Programming Language
    "76155785",   # Telecommunications
    "527648132",  # Information Security

    # Level 2 - Secondary disciplines
    "90509273",   # Robot
    "34413123",   # Robotics
    "19966478",   # Mobile Robot
    "110875604",  # The Internet
}

# Threshold for filtering non-CS background authors
# Authors with CS score below this threshold will not be synced to Talent
# Set to 0.5 to ensure only authors with strong CS background are included
CS_SCORE_THRESHOLD = 0.5

# Log module load to verify code version
logger.info(f"[CS_CONCEPTS] Module loaded. Concepts: {len(CORE_CS_CONCEPTS)}, Threshold: {CS_SCORE_THRESHOLD}")
