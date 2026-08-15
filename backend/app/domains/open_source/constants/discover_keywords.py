"""Search keyword seeds for the auto-discover feature (taxonomy v2).

Maps each tech direction code (75 directions from the shared taxonomy) to
GitHub search queries. Each query is combined with ``stars:>={threshold}``
at runtime; per-domain threshold overrides live in the shared taxonomy
(DOMAIN_MIN_STARS_OVERRIDE) and are applied by discover_service.

Keep keys in sync with TECH_DIRECTIONS in
app/domains/shared/constants/tech_taxonomy.py — directions without an entry
here are skipped by the discovery run.
"""

from app.domains.shared.constants.tech_taxonomy import (  # noqa: F401  (re-export)
    DIRECTION_TO_DOMAIN,
    DIRECTION_TO_ELEMENT,
    DOMAIN_MIN_STARS_OVERRIDE,
)

DIRECTION_SEARCH_KEYWORDS: dict[str, list[str]] = {
    # ── basic_software / os ──
    "os_kernel": ["topic:operating-system topic:kernel", "topic:operating-system c"],
    # ── basic_software / db_storage ──
    "databases": ["topic:database", "topic:sql-database"],
    "cache": ["topic:in-memory-database", "topic:cache key-value"],
    "storage": ["topic:distributed-storage", "topic:object-storage"],
    # ── basic_software / languages ──
    "programming_languages": ["topic:programming-language"],
    # ── basic_software / toolchain ──
    "compilers": ["topic:compiler"],
    "build_tools": ["topic:build-system", "topic:build-tools"],
    # ── basic_software / middleware ──
    "message_queue": ["topic:message-broker", "topic:message-queue"],
    "web_server": ["topic:web-server", "topic:http-server"],
    "api_gateway": ["topic:api-gateway"],
    # ── basic_software / browser ──
    "browser_engines": ["topic:browser-engine", "topic:web-browser engine"],
    "js_engines": ["topic:javascript-engine", "topic:jit javascript"],
    # ── ai_models / models ──
    "llm": ["topic:llm large language model", "topic:large-language-models"],
    "vlm": ["topic:vision-language-model", "topic:multimodal model"],
    "gen_models": ["topic:stable-diffusion", "topic:generative diffusion"],
    "speech_models": ["topic:speech-recognition", "topic:text-to-speech"],
    "ai_safety": ["topic:ai-safety", "topic:ai-alignment"],
    # ── ai_models / training ──
    "training_frameworks": ["topic:deep-learning framework", "topic:distributed-training"],
    # ── ai_models / inference ──
    "llm_inference": ["topic:llm-inference", "topic:inference-engine"],
    "model_serving": ["topic:model-serving", "topic:ml-serving"],
    # ── ai_apps / agents ──
    "agent_frameworks": ["topic:ai-agent", "topic:agent-framework"],
    "rag": ["topic:rag retrieval", "topic:retrieval-augmented-generation"],
    "ai_coding": ["topic:ai-coding-assistant", "ai code assistant"],
    # ── ai_apps / ai_engineering ──
    "mlops": ["topic:mlops", "topic:ml-ops"],
    "vector_db": ["topic:vector-database"],
    # ── ai_apps / apps ──
    "ai_applications": ["topic:ai-tools", "topic:chatgpt app"],
    "cv_applications": ["topic:computer-vision", "topic:object-detection"],
    # ── communications / protocols ──
    "network_stack": ["topic:proxy server", "topic:network-programming"],
    "sdn": ["topic:sdn", "topic:software-defined-networking"],
    "iot_protocols": ["topic:mqtt", "topic:iot protocol"],
    # ── communications / wireless ──
    "cellular": ["topic:5g", "topic:lte network"],
    "sdr": ["topic:software-defined-radio", "topic:sdr"],
    # ── communications / network_simulation ──
    "network_simulation": ["topic:network-simulator", "ns-3 network simulation"],
    # ── computing / hpc ──
    "hpc": ["topic:hpc", "topic:parallel-computing"],
    "gpu_computing": ["topic:gpu-computing", "topic:cuda library"],
    # ── computing / cloud_native ──
    "containers": ["topic:containers runtime", "topic:container"],
    "orchestration": ["topic:kubernetes", "topic:container-orchestration"],
    "service_mesh": ["topic:service-mesh"],
    "observability": ["topic:observability", "topic:monitoring"],
    "cicd": ["topic:ci-cd", "topic:continuous-integration"],
    "serverless": ["topic:serverless", "topic:faas"],
    # ── computing / virtualization ──
    "virtualization": ["topic:virtualization", "topic:hypervisor"],
    # ── computing / silicon ──
    "risc_v": ["topic:risc-v"],
    # ── modeling_simulation / sci_compute ──
    "numerical": ["topic:numerical", "topic:scientific-computing"],
    "optimization": ["topic:optimization-solver", "topic:mathematical-optimization"],
    # ── modeling_simulation / simulation ──
    "cfd_fem": ["topic:computational-fluid-dynamics", "topic:finite-element"],
    "cad_cae": ["topic:cad", "topic:computer-aided-design"],
    # ── modeling_simulation / math_libs ──
    "symbolic_math": ["topic:symbolic-mathematics", "topic:computer-algebra"],
    # ── trusted_security / sys_sec ──
    "network_security": ["topic:network-security", "topic:firewall"],
    "appsec": ["topic:application-security", "topic:security-tools scanner"],
    "host_security": ["topic:endpoint-security", "topic:intrusion-detection"],
    # ── trusted_security / sec_ops ──
    "pentest": ["topic:penetration-testing", "topic:exploit-framework"],
    "vuln_management": ["topic:vulnerability-scanner", "topic:vulnerability-detection"],
    "siem_analysis": ["topic:siem", "topic:security-analytics"],
    "threat_intel": ["topic:threat-intelligence", "topic:cybersecurity intelligence"],
    # ── trusted_security / crypto_trust ──
    "cryptography": ["topic:cryptography", "topic:encryption library"],
    "privacy_computing": ["topic:privacy-preserving", "topic:homomorphic-encryption"],
    "identity_auth": ["topic:identity-provider", "topic:authentication sso"],
    # ── multimedia / av ──
    "media_framework": ["topic:ffmpeg", "topic:media-processing"],
    "streaming": ["topic:streaming-media", "topic:live-streaming server"],
    "codecs": ["topic:video-codec", "topic:audio-codec"],
    "media_players": ["topic:media-player", "topic:video-player"],
    "webrtc": ["topic:webrtc", "topic:real-time-communication"],
    # ── multimedia / graphics ──
    "rendering": ["topic:rendering-engine", "topic:webgl"],
    "image_processing": ["topic:image-processing", "topic:computer-graphics"],
    "graphics_libs": ["topic:graphics-library", "topic:gpu graphics library"],
    "game_engines": ["topic:game-engine", "topic:gamedev engine"],
    # ── robotics ──
    "robot_middleware": ["topic:robot-operating-system", "topic:ros2"],
    "motion_planning": ["topic:motion-planning", "topic:robotics control"],
    "robot_perception": ["topic:slam", "topic:robotics-perception"],
    "embodied_ai": ["topic:embodied-ai", "topic:robot-learning"],
    # ── autonomous_driving ──
    "ad_stacks": ["topic:autonomous-driving", "topic:self-driving"],
    "ad_perception": ["topic:lidar", "topic:autonomous-driving perception"],
    "ad_planning": ["topic:autonomous-vehicles planning", "topic:autonomous-driving control"],
    "ad_simulation": ["topic:autonomous-driving simulation", "topic:carla simulator"],
}
