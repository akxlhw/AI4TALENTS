"""Platform tech taxonomy — single source of truth (v2, 2026-08).

Replaces the legacy 6-domain taxonomy (ai/robotics/data_science/networks/
systems/security) with a 3-layer classification:

    技术领域 TechDomain (10) → 技术要素 element (34) → 技术方向 TechDirection (~76)

Key decisions (user-approved):
- ``os_repo_config.tech_element`` valid values = ELEMENT layer codes (34),
  not domain codes — matches the field name and keeps filtering granular.
- robotics and autonomous_driving are standalone domains.
- Game engines live under multimedia/graphics.

Consumed by: scripts/data seeds, open-source VALID_TECH_ELEMENTS,
auto-discover keywords, and the 062 data migration.
"""

from __future__ import annotations

# ============ Layer 1: 技术领域 (10) ============

TECH_DOMAINS: list[dict] = [
    {"code": "basic_software", "name": "基础软件", "name_en": "Basic Software", "sort": 1},
    {"code": "ai_models", "name": "AI大模型", "name_en": "AI Large Models", "sort": 2},
    {"code": "ai_apps", "name": "AI软件", "name_en": "AI Software", "sort": 3},
    {"code": "communications", "name": "通信技术", "name_en": "Communications", "sort": 4},
    {"code": "computing", "name": "计算技术", "name_en": "Computing", "sort": 5},
    {
        "code": "modeling_simulation",
        "name": "建模仿真与数学应用",
        "name_en": "Modeling, Simulation & Math",
        "sort": 6,
    },
    {"code": "trusted_security", "name": "可信安全", "name_en": "Trusted Security", "sort": 7},
    {"code": "multimedia", "name": "多媒体", "name_en": "Multimedia", "sort": 8},
    {"code": "robotics", "name": "机器人", "name_en": "Robotics", "sort": 9},
    {"code": "autonomous_driving", "name": "自动驾驶", "name_en": "Autonomous Driving", "sort": 10},
]

# ============ Layer 2: 技术要素 (34) ============
# code → {name, name_en, domain}

TECH_ELEMENTS: dict[str, dict] = {
    # — 基础软件 —
    "os": {"name": "操作系统", "name_en": "Operating Systems", "domain": "basic_software"},
    "db_storage": {
        "name": "数据库与存储",
        "name_en": "Databases & Storage",
        "domain": "basic_software",
    },
    "languages": {
        "name": "编程语言",
        "name_en": "Programming Languages",
        "domain": "basic_software",
    },
    "toolchain": {
        "name": "编译与构建",
        "name_en": "Compilers & Build Tools",
        "domain": "basic_software",
    },
    "middleware": {"name": "中间件", "name_en": "Middleware", "domain": "basic_software"},
    "browser": {
        "name": "浏览器与引擎",
        "name_en": "Browsers & Engines",
        "domain": "basic_software",
    },
    # — AI大模型 —
    "models": {"name": "模型", "name_en": "Models", "domain": "ai_models"},
    "training": {"name": "训练", "name_en": "Training", "domain": "ai_models"},
    "inference": {"name": "推理", "name_en": "Inference", "domain": "ai_models"},
    # — AI软件 —
    "agents": {"name": "智能体与工具", "name_en": "Agents & Tools", "domain": "ai_apps"},
    "ai_engineering": {"name": "AI工程", "name_en": "AI Engineering", "domain": "ai_apps"},
    "apps": {"name": "应用", "name_en": "Applications", "domain": "ai_apps"},
    # — 通信技术 —
    "protocols": {
        "name": "网络协议与栈",
        "name_en": "Protocols & Stacks",
        "domain": "communications",
    },
    "wireless": {"name": "无线通信", "name_en": "Wireless", "domain": "communications"},
    "network_simulation": {
        "name": "网络仿真",
        "name_en": "Network Simulation",
        "domain": "communications",
    },
    # — 计算技术 —
    "hpc": {"name": "高性能计算", "name_en": "High-Performance Computing", "domain": "computing"},
    "cloud_native": {"name": "云原生", "name_en": "Cloud Native", "domain": "computing"},
    "virtualization": {"name": "虚拟化", "name_en": "Virtualization", "domain": "computing"},
    "silicon": {"name": "开源芯片", "name_en": "Open Silicon", "domain": "computing"},
    # — 建模仿真与数学应用 —
    "sci_compute": {
        "name": "科学计算",
        "name_en": "Scientific Computing",
        "domain": "modeling_simulation",
    },
    "simulation": {"name": "仿真", "name_en": "Simulation", "domain": "modeling_simulation"},
    "math_libs": {"name": "数学库", "name_en": "Math Libraries", "domain": "modeling_simulation"},
    # — 可信安全 —
    "sys_sec": {
        "name": "系统与网络安全",
        "name_en": "System & Network Security",
        "domain": "trusted_security",
    },
    "sec_ops": {
        "name": "攻防与检测",
        "name_en": "Security Operations",
        "domain": "trusted_security",
    },
    "crypto_trust": {
        "name": "密码与信任",
        "name_en": "Cryptography & Trust",
        "domain": "trusted_security",
    },
    # — 多媒体 —
    "av": {"name": "音视频", "name_en": "Audio & Video", "domain": "multimedia"},
    "graphics": {"name": "图形图像", "name_en": "Graphics & Imaging", "domain": "multimedia"},
    # — 机器人 —
    "robot_control": {"name": "本体与控制", "name_en": "Robot Control", "domain": "robotics"},
    "robot_perception": {"name": "感知", "name_en": "Robot Perception", "domain": "robotics"},
    "embodied": {"name": "具身智能", "name_en": "Embodied AI", "domain": "robotics"},
    # — 自动驾驶 —
    "ad_platforms": {"name": "全栈平台", "name_en": "AD Platforms", "domain": "autonomous_driving"},
    "ad_perception": {
        "name": "感知与定位",
        "name_en": "AD Perception & Localization",
        "domain": "autonomous_driving",
    },
    "ad_planning": {
        "name": "规划控制",
        "name_en": "AD Planning & Control",
        "domain": "autonomous_driving",
    },
    "ad_simulation": {"name": "仿真", "name_en": "AD Simulation", "domain": "autonomous_driving"},
}

VALID_TECH_ELEMENTS = set(TECH_ELEMENTS.keys())

# ============ Layer 3: 技术方向 (~76) ============
# (direction_code, 中文名, 英文名, element_code)

TECH_DIRECTIONS: list[tuple[str, str, str, str]] = [
    # — basic_software / os —
    ("os_kernel", "操作系统与内核", "OS & Kernels", "os"),
    # — basic_software / db_storage —
    ("databases", "数据库", "Databases", "db_storage"),
    ("cache", "缓存中间件", "Caching", "db_storage"),
    ("storage", "分布式存储", "Distributed Storage", "db_storage"),
    # — basic_software / languages —
    ("programming_languages", "编程语言与实现", "Programming Languages", "languages"),
    # — basic_software / toolchain —
    ("compilers", "编译器", "Compilers", "toolchain"),
    ("build_tools", "构建系统", "Build Tools", "toolchain"),
    # — basic_software / middleware —
    ("message_queue", "消息队列", "Message Queues", "middleware"),
    ("web_server", "Web服务", "Web Servers", "middleware"),
    ("api_gateway", "API网关", "API Gateways", "middleware"),
    # — basic_software / browser —
    ("browser_engines", "浏览器引擎", "Browser Engines", "browser"),
    ("js_engines", "JS引擎", "JavaScript Engines", "browser"),
    # — ai_models / models —
    ("llm", "大语言模型", "Large Language Models", "models"),
    ("vlm", "多模态大模型", "Vision-Language Models", "models"),
    ("gen_models", "生成模型", "Generative Models", "models"),
    ("speech_models", "语音大模型", "Speech Models", "models"),
    ("ai_safety", "AI安全与对齐", "AI Safety & Alignment", "models"),
    # — ai_models / training —
    ("training_frameworks", "训练框架", "Training Frameworks", "training"),
    # — ai_models / inference —
    ("llm_inference", "推理引擎", "LLM Inference Engines", "inference"),
    ("model_serving", "模型服务化", "Model Serving", "inference"),
    # — ai_apps / agents —
    ("agent_frameworks", "智能体框架", "Agent Frameworks", "agents"),
    ("rag", "检索增强生成", "RAG", "agents"),
    ("ai_coding", "AI编程辅助", "AI Coding Assistants", "agents"),
    # — ai_apps / ai_engineering —
    ("mlops", "MLOps流水线", "MLOps", "ai_engineering"),
    ("vector_db", "向量数据库", "Vector Databases", "ai_engineering"),
    # — ai_apps / apps —
    ("ai_applications", "AI应用", "AI Applications", "apps"),
    ("cv_applications", "计算机视觉应用", "CV Applications", "apps"),
    # — communications / protocols —
    ("network_stack", "高性能网络栈", "Network Stacks", "protocols"),
    ("sdn", "软件定义网络", "SDN", "protocols"),
    ("iot_protocols", "物联网协议", "IoT Protocols", "protocols"),
    # — communications / wireless —
    ("cellular", "移动通信", "Cellular (5G/6G)", "wireless"),
    ("sdr", "软件无线电", "Software-Defined Radio", "wireless"),
    # — communications / network_simulation —
    ("network_simulation", "网络仿真", "Network Simulation", "network_simulation"),
    # — computing / hpc —
    ("hpc", "并行计算", "Parallel & HPC", "hpc"),
    ("gpu_computing", "GPU计算", "GPU Computing", "hpc"),
    # — computing / cloud_native —
    ("containers", "容器", "Containers", "cloud_native"),
    ("orchestration", "编排调度", "Orchestration", "cloud_native"),
    ("service_mesh", "服务网格", "Service Mesh", "cloud_native"),
    ("observability", "可观测性", "Observability", "cloud_native"),
    ("cicd", "CI/CD", "CI/CD", "cloud_native"),
    ("serverless", "Serverless", "Serverless", "cloud_native"),
    # — computing / virtualization —
    ("virtualization", "虚拟化", "Virtualization", "virtualization"),
    # — computing / silicon —
    ("risc_v", "RISC-V与开源芯片", "RISC-V & Open Silicon", "silicon"),
    # — modeling_simulation / sci_compute —
    ("numerical", "数值计算", "Numerical Computing", "sci_compute"),
    ("optimization", "优化求解", "Optimization Solvers", "sci_compute"),
    # — modeling_simulation / simulation —
    ("cfd_fem", "流体/有限元", "CFD & FEM", "simulation"),
    ("cad_cae", "CAD/CAE", "CAD & CAE", "simulation"),
    # — modeling_simulation / math_libs —
    ("symbolic_math", "符号计算", "Symbolic Math", "math_libs"),
    # — trusted_security / sys_sec —
    ("network_security", "网络安全", "Network Security", "sys_sec"),
    ("appsec", "应用安全", "Application Security", "sys_sec"),
    ("host_security", "主机安全/EDR", "Host Security / EDR", "sys_sec"),
    # — trusted_security / sec_ops —
    ("pentest", "渗透测试", "Penetration Testing", "sec_ops"),
    ("vuln_management", "漏洞管理", "Vulnerability Management", "sec_ops"),
    ("siem_analysis", "安全分析/SIEM", "SIEM & Security Analytics", "sec_ops"),
    ("threat_intel", "威胁情报", "Threat Intelligence", "sec_ops"),
    # — trusted_security / crypto_trust —
    ("cryptography", "密码学", "Cryptography", "crypto_trust"),
    ("privacy_computing", "隐私计算", "Privacy Computing", "crypto_trust"),
    ("identity_auth", "身份认证", "Identity & Auth", "crypto_trust"),
    # — multimedia / av —
    ("media_framework", "媒体处理框架", "Media Frameworks", "av"),
    ("streaming", "流媒体", "Streaming Media", "av"),
    ("codecs", "编解码", "Codecs", "av"),
    ("media_players", "播放器", "Media Players", "av"),
    ("webrtc", "实时音视频", "WebRTC / RTC", "av"),
    # — multimedia / graphics —
    ("rendering", "渲染引擎", "Rendering Engines", "graphics"),
    ("image_processing", "图像处理", "Image Processing", "graphics"),
    ("graphics_libs", "图形库", "Graphics Libraries", "graphics"),
    ("game_engines", "游戏引擎", "Game Engines", "graphics"),
    # — robotics —
    ("robot_middleware", "机器人中间件", "Robot Middleware", "robot_control"),
    ("motion_planning", "运动规划与控制", "Motion Planning & Control", "robot_control"),
    ("robot_perception", "感知与SLAM", "Perception & SLAM", "robot_perception"),
    ("embodied_ai", "具身智能操作", "Embodied AI", "embodied"),
    # — autonomous_driving —
    ("ad_stacks", "全栈平台", "AD Full Stacks", "ad_platforms"),
    ("ad_perception", "感知定位", "AD Perception", "ad_perception"),
    ("ad_planning", "规划控制", "AD Planning & Control", "ad_planning"),
    ("ad_simulation", "自动驾驶仿真", "AD Simulation", "ad_simulation"),
]

# direction_code → element_code (derived; kept as dict for O(1) lookups)
DIRECTION_TO_ELEMENT: dict[str, str] = {d[0]: d[3] for d in TECH_DIRECTIONS}

# direction_code → domain_code
DIRECTION_TO_DOMAIN: dict[str, str] = {
    code: TECH_ELEMENTS[element]["domain"] for code, _, _, element in TECH_DIRECTIONS
}

# ============ Discovery: per-domain star threshold overrides ============
# These domains have systematically lower star counts on GitHub; the default
# 30k global threshold would return nothing. Overrides REPLACE the user's
# global threshold for directions in these domains.
DOMAIN_MIN_STARS_OVERRIDE: dict[str, int] = {
    "robotics": 3000,
    "modeling_simulation": 5000,
    "autonomous_driving": 8000,
    "communications": 8000,
    "trusted_security": 15000,
}

# ============ Migration maps: legacy v1 → v2 ============

# Old direction code → new direction code.
# - Same code (id preserved in place, domain/element updated by migration)
# - Renamed code (row updated in place, id preserved)
# - Merged code (references moved to target, old row deleted)
OLD_DIRECTION_REMAP: dict[str, str] = {
    # preserved (same code, re-parented)
    "llm": "llm",
    "llm_inference": "llm_inference",
    "databases": "databases",
    "network_security": "network_security",
    "privacy_computing": "privacy_computing",
    "mlops": "mlops",
    "embodied_ai": "embodied_ai",
    "motion_planning": "motion_planning",
    "robot_perception": "robot_perception",
    "ai_safety": "ai_safety",
    # renamed in place
    "cv": "cv_applications",
    "speech": "speech_models",
    "multimodal": "vlm",
    # merged into existing new rows (refs remapped, old row deleted)
    "nlp": "llm",
    "recsys": "ai_applications",
    "search_tech": "ai_applications",
    "rl": "training_frameworks",
    "ai_infra": "training_frameworks",
    "data_engineering": "databases",
    "bi_analytics": "numerical",
    "distributed_systems": "orchestration",
    "autonomous_driving": "ad_stacks",
}

# Old domain code → element code fallback (for repos not in the explicit map)
OLD_DOMAIN_ELEMENT_FALLBACK: dict[str, str] = {
    "ai": "models",
    "robotics": "robot_control",
    "data_science": "sci_compute",
    "networks": "protocols",
    "systems": "cloud_native",
    "security": "sys_sec",
}

# Explicit per-repo element mapping for the 43 seeded repos (old element was
# the legacy domain code; ai repos split between ai_models / ai_apps / computing).
# NOTE: values are ELEMENT codes (decision A), not direction codes.
OLD_REPO_ELEMENT_MAP: dict[str, str] = {
    # ai → split
    "pytorch/pytorch": "training",
    "tensorflow/tensorflow": "training",
    "huggingface/transformers": "models",
    "scikit-learn/scikit-learn": "models",
    "microsoft/DeepSpeed": "training",
    "apache/spark": "db_storage",
    "langchain-ai/langchain": "agents",
    "langgenius/dify": "agents",
    "huggingface/trl": "training",
    "sgl-project/sglang": "inference",
    "huggingface/text-generation-inference": "inference",
    "ray-project/ray": "training",
    "NVIDIA/Megatron-LM": "training",
    "google/jax": "training",
    "apache/tvm": "inference",
    "NVIDIA/cutlass": "hpc",
    # robotics → new robotics domain
    "ros/ros": "robot_control",
    "ros2/ros2": "robot_control",
    "ArduPilot/ardupilot": "robot_control",
    "NVIDIA-Omniverse/IsaacSim": "embodied",
    "google-research/google-research": "models",
    # data_science → modeling / basic_software / ai_apps
    "pandas-dev/pandas": "sci_compute",
    "numpy/numpy": "sci_compute",
    "jupyter/jupyter": "ai_engineering",
    "matplotlib/matplotlib": "sci_compute",
    "apache/arrow": "db_storage",
    "dask/dask": "hpc",
    # networks → communications (+ linux to os!)
    "torvalds/linux": "os",
    "envoyproxy/envoy": "protocols",
    "grpc/grpc": "protocols",
    "openvswitch/ovs": "protocols",
    "cloudflare/cloudflared": "protocols",
    "FRRouting/frr": "protocols",
    # systems → split
    "golang/go": "languages",
    "rust-lang/rust": "languages",
    "kubernetes/kubernetes": "cloud_native",
    "moby/moby": "cloud_native",
    "redis/redis": "db_storage",
    "apache/kafka": "middleware",
    # security → split
    "zaproxy/zaproxy": "sys_sec",
    "rapid7/metasploit-framework": "sec_ops",
    "sqlmapproject/sqlmap": "sec_ops",
    "nmap/nmap": "sys_sec",
    "mitmproxy/mitmproxy": "sys_sec",
    "wireshark/wireshark": "sys_sec",
}
