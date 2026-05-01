"""
Seed script for open source repository configurations.
Pre-configures 35 repositories across 6 tech elements.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.open_source import OSRepoConfig


SEED_REPOS = [
    # AI
    {"repo_full_name": "pytorch/pytorch", "display_name": "PyTorch", "tech_element": "ai", "language": "Python", "description": "Tensors and Dynamic neural networks in Python with strong GPU acceleration"},
    {"repo_full_name": "tensorflow/tensorflow", "display_name": "TensorFlow", "tech_element": "ai", "language": "Python", "description": "An Open Source Machine Learning Framework for Everyone"},
    {"repo_full_name": "huggingface/transformers", "display_name": "Hugging Face Transformers", "tech_element": "ai", "language": "Python", "description": "State-of-the-art Machine Learning for JAX, PyTorch and TensorFlow"},
    {"repo_full_name": "scikit-learn/scikit-learn", "display_name": "scikit-learn", "tech_element": "ai", "language": "Python", "description": "scikit-learn: machine learning in Python"},
    {"repo_full_name": "microsoft/DeepSpeed", "display_name": "DeepSpeed", "tech_element": "ai", "language": "Python", "description": "Deep learning optimization library"},
    {"repo_full_name": "apache/spark", "display_name": "Apache Spark", "tech_element": "ai", "language": "Scala", "description": "Apache Spark - A unified analytics engine for large-scale data processing"},
    # Robotics
    {"repo_full_name": "ros/ros", "display_name": "ROS", "tech_element": "robotics", "language": "Python", "description": "Robot Operating System"},
    {"repo_full_name": "ros2/ros2", "display_name": "ROS2", "tech_element": "robotics", "language": "Python", "description": "ROS 2 - Robot Operating System 2"},
    {"repo_full_name": "ArduPilot/ardupilot", "display_name": "ArduPilot", "tech_element": "robotics", "language": "C++", "description": "ArduPilot is the most advanced, full-featured open source autopilot software"},
    {"repo_full_name": "NVIDIA-Omniverse/IsaacSim", "display_name": "NVIDIA Isaac Sim", "tech_element": "robotics", "language": "Python", "description": "NVIDIA Isaac Sim - Robotics simulation platform"},
    {"repo_full_name": "google-research/google-research", "display_name": "Google Research", "tech_element": "robotics", "language": "Python", "description": "Google Research repository"},
    # Data Science
    {"repo_full_name": "pandas-dev/pandas", "display_name": "pandas", "tech_element": "data_science", "language": "Python", "description": "Powerful data structures for data analysis"},
    {"repo_full_name": "numpy/numpy", "display_name": "NumPy", "tech_element": "data_science", "language": "Python", "description": "The fundamental package for scientific computing with Python"},
    {"repo_full_name": "jupyter/jupyter", "display_name": "Jupyter", "tech_element": "data_science", "language": "Python", "description": "Jupyter metapackage for installation and docs"},
    {"repo_full_name": "matplotlib/matplotlib", "display_name": "Matplotlib", "tech_element": "data_science", "language": "Python", "description": "matplotlib: plotting with Python"},
    {"repo_full_name": "apache/arrow", "display_name": "Apache Arrow", "tech_element": "data_science", "language": "C++", "description": "Apache Arrow is a multi-language toolbox for accelerated data interchange"},
    {"repo_full_name": "dask/dask", "display_name": "Dask", "tech_element": "data_science", "language": "Python", "description": "Parallel computing with task scheduling"},
    # Networks
    {"repo_full_name": "torvalds/linux", "display_name": "Linux Kernel", "tech_element": "networks", "language": "C", "description": "Linux kernel source tree"},
    {"repo_full_name": "envoyproxy/envoy", "display_name": "Envoy", "tech_element": "networks", "language": "C++", "description": "Cloud-native high-performance edge/middle/service proxy"},
    {"repo_full_name": "grpc/grpc", "display_name": "gRPC", "tech_element": "networks", "language": "C++", "description": "The C based gRPC (C++, Python, Ruby, Objective-C, PHP, C#)"},
    {"repo_full_name": "openvswitch/ovs", "display_name": "Open vSwitch", "tech_element": "networks", "language": "C", "description": "Open vSwitch is a production quality, multilayer virtual switch"},
    {"repo_full_name": "cloudflare/cloudflared", "display_name": "Cloudflared", "tech_element": "networks", "language": "Go", "description": "Cloudflare Tunnel client"},
    {"repo_full_name": "FRRouting/frr", "display_name": "FRRouting", "tech_element": "networks", "language": "C", "description": "FRRouting is free software that manages TCP/IP based routing protocols"},
    # Systems
    {"repo_full_name": "golang/go", "display_name": "Go", "tech_element": "systems", "language": "Go", "description": "The Go programming language"},
    {"repo_full_name": "rust-lang/rust", "display_name": "Rust", "tech_element": "systems", "language": "Rust", "description": "Empowering everyone to build reliable and efficient software"},
    {"repo_full_name": "kubernetes/kubernetes", "display_name": "Kubernetes", "tech_element": "systems", "language": "Go", "description": "Production-Grade Container Scheduling and Management"},
    {"repo_full_name": "moby/moby", "display_name": "Docker", "tech_element": "systems", "language": "Go", "description": "Moby Project - a collaborative project for the container ecosystem"},
    {"repo_full_name": "redis/redis", "display_name": "Redis", "tech_element": "systems", "language": "C", "description": "Redis is an in-memory database that persists on disk"},
    {"repo_full_name": "apache/kafka", "display_name": "Apache Kafka", "tech_element": "systems", "language": "Java", "description": "Mirror of Apache Kafka"},
    # Security
    {"repo_full_name": "zaproxy/zaproxy", "display_name": "OWASP ZAP", "tech_element": "security", "language": "Java", "description": "The OWASP ZAP core project"},
    {"repo_full_name": "rapid7/metasploit-framework", "display_name": "Metasploit", "tech_element": "security", "language": "Ruby", "description": "Metasploit Framework"},
    {"repo_full_name": "sqlmapproject/sqlmap", "display_name": "sqlmap", "tech_element": "security", "language": "Python", "description": "Automatic SQL injection and database takeover tool"},
    {"repo_full_name": "nmap/nmap", "display_name": "Nmap", "tech_element": "security", "language": "C", "description": "Nmap - the Network Mapper"},
    {"repo_full_name": "mitmproxy/mitmproxy", "display_name": "mitmproxy", "tech_element": "security", "language": "Python", "description": "An interactive TLS-capable intercepting HTTP proxy"},
    {"repo_full_name": "wireshark/wireshark", "display_name": "Wireshark", "tech_element": "security", "language": "C", "description": "Wireshark - Network traffic analyzer"},
]


async def seed() -> None:
    async with async_session_factory() as session:
        inserted = 0
        skipped = 0
        counts: dict[str, int] = {}

        for repo in SEED_REPOS:
            existing = await session.scalar(
                select(OSRepoConfig).where(OSRepoConfig.repo_full_name == repo["repo_full_name"])
            )
            if existing:
                skipped += 1
                counts[repo["tech_element"]] = counts.get(repo["tech_element"], 0)
                continue

            config = OSRepoConfig(
                repo_full_name=repo["repo_full_name"],
                display_name=repo["display_name"],
                description=repo.get("description"),
                tech_element=repo["tech_element"],
                language=repo.get("language"),
                is_active=True,
                collect_enabled=True,
            )
            session.add(config)
            inserted += 1
            counts[repo["tech_element"]] = counts.get(repo["tech_element"], 0) + 1

        await session.commit()

        print(f"Seeded {inserted} OS repo configs, skipped {skipped} duplicates.")
        print("\nBy tech element:")
        for tech, count in sorted(counts.items()):
            if count > 0:
                print(f"  {tech}: {count} repos")


if __name__ == "__main__":
    asyncio.run(seed())
