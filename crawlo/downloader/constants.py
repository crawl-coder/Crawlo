#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Downloader Constants Configuration
===================================

Provides browser startup parameter optimization for anti-detection.
Includes:
- Harmful arguments to ignore
- Default browser parameters for performance optimization
- Stealth mode parameters
- WebRTC protection parameters
- WebGL disable parameters
- Canvas fingerprint protection
- Resource type blocking configuration
- Ad domain blacklist
"""

# 需要忽略的有害参数（这些参数可能暴露自动化特征）
HARMFUL_ARGS = (
    "--enable-automation",
    "--disable-popup-blocking",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-extensions",
)

# 默认浏览器参数（性能优化）
DEFAULT_ARGS = (
    "--no-pings",
    "--no-first-run",
    "--disable-infobars",
    "--disable-breakpad",
    "--no-service-autorun",
    "--homepage=about:blank",
    "--password-store=basic",
    "--disable-hang-monitor",
    "--no-default-browser-check",
    "--disable-session-crashed-bubble",
    "--disable-search-engine-choice-screen",
)

# 隐身模式参数
STEALTH_ARGS = (
    # 性能和隐私优化
    "--test-type",
    "--lang=zh-CN",
    "--mute-audio",
    "--disable-sync",
    "--hide-scrollbars",
    "--disable-logging",
    "--start-maximized",
    "--enable-async-dns",
    "--use-mock-keychain",
    "--disable-translate",
    "--disable-voice-input",
    "--window-position=0,0",
    "--disable-wake-on-wifi",
    "--ignore-gpu-blocklist",
    "--enable-tcp-fast-open",
    "--disable-cloud-import",
    "--disable-print-preview",
    "--disable-dev-shm-usage",
    "--metrics-recording-only",
    "--disable-crash-reporter",
    "--disable-partial-raster",
    "--disable-gesture-typing",
    "--disable-checker-imaging",
    "--disable-prompt-on-repost",
    "--force-color-profile=srgb",
    "--font-render-hinting=none",
    "--aggressive-cache-discard",
    "--disable-cookie-encryption",
    "--disable-domain-reliability",
    "--disable-threaded-animation",
    "--disable-threaded-scrolling",
    "--enable-simple-cache-backend",
    "--disable-background-networking",
    "--enable-surface-synchronization",
    "--disable-image-animation-resync",
    "--disable-renderer-backgrounding",
    "--disable-ipc-flooding-protection",
    "--safebrowsing-disable-auto-update",
    "--disable-offer-upload-credit-cards",
    "--disable-background-timer-throttling",
    "--disable-new-content-rendering-timeout",
    "--run-all-compositor-stages-before-draw",
    "--disable-client-side-phishing-detection",
    "--disable-backgrounding-occluded-windows",
    "--disable-layer-tree-host-memory-pressure",
    "--autoplay-policy=user-gesture-required",
    "--disable-offer-store-unmasked-wallet-cards",
    "--disable-component-extensions-with-background-pages",
    # 关键反检测参数
    "--disable-blink-features=AutomationControlled",
    "--enable-features=NetworkService,NetworkServiceInProcess,TrustTokens,TrustTokensAlwaysAllowIssuance",
    "--blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4",
    "--disable-features=AudioServiceOutOfProcess,TranslateUI,BlinkGenPropertyTrees",
)

# WebRTC 保护参数
WEBRTC_PROTECTION_ARGS = (
    "--webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--force-webrtc-ip-handling-policy",
)

# WebGL 禁用参数
WEBGL_DISABLE_ARGS = (
    "--disable-webgl",
    "--disable-webgl-image-chromium",
    "--disable-webgl2",
)

# Canvas 指纹保护参数
CANVAS_NOISE_ARG = "--fingerprinting-canvas-image-data-noise"

# 屏蔽的资源类型（用于加速加载）
EXTRA_RESOURCES = {
    "font",
    "image",
    "media",
    "beacon",
    "object",
    "imageset",
    "texttrack",
    "websocket",
    "csp_report",
    "stylesheet",
}

# 广告域名黑名单
AD_DOMAINS = {
    'googlesyndication.com',
    'doubleclick.net',
    'googleadservices.com',
    'google-analytics.com',
    'googletagmanager.com',
    'facebook.com/tr',
    'connect.facebook.net',
    'adservice.google.com',
    'ads.twitter.com'
}
