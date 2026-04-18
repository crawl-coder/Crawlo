#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
DrissionPage 反检测脚本

DrissionPage 使用真实 Chrome 浏览器，自动化特征较少，
但仍需隐藏 webdriver 标识以绕过基础反爬检测。
"""

DRISSIONPAGE_STEALTH_SCRIPT = """
// ========== DrissionPage 反检测脚本 ==========

// 1. 隐藏 webdriver 标识
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true
});

// 删除原型链上的 webdriver
delete Navigator.prototype.webdriver;

// 2. 伪造 plugins（模拟真实浏览器插件）
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            {
                name: 'Chrome PDF Plugin',
                description: 'Portable Document Format',
                filename: 'internal-pdf-viewer',
                length: 1
            },
            {
                name: 'Chrome PDF Viewer',
                description: '',
                filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                length: 1
            },
            {
                name: 'Native Client',
                description: '',
                filename: 'internal-nacl-plugin',
                length: 2
            }
        ];
        plugins.item = (index) => plugins[index] || null;
        plugins.namedItem = (name) => plugins.find(p => p.name === name) || null;
        plugins.refresh = () => {};
        return plugins;
    },
    configurable: true
});

// 3. 伪造 languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en-US', 'en'],
    configurable: true
});

// 4. 伪造 platform
Object.defineProperty(navigator, 'platform', {
    get: () => 'Win32',
    configurable: true
});

// 5. 伪造 hardwareConcurrency（CPU 核心数）
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8,
    configurable: true
});

// 6. 伪造 deviceMemory
Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8,
    configurable: true
});

// 7. 修改权限查询（避免 permissions API 泄露自动化特征）
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => {
    if (parameters.name === 'notifications') {
        return Promise.resolve({ state: Notification.permission });
    }
    if (parameters.name === 'geolocation') {
        return Promise.resolve({ state: 'prompt' });
    }
    return originalQuery(parameters);
};

// 8. 隐藏自动化相关的 window 属性
delete window.__playwright;
delete window.__pw_manual;
delete window.__PW_inspect;

// 9. 伪造 Chrome 特有属性
window.chrome = {
    app: {
        isInstalled: false,
        InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
        RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }
    },
    runtime: {
        OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
        OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
        PlatformArch: { ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
        PlatformNaclArch: { ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
        PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
        RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' },
        connect: function() { return { onDisconnect: { addListener: function() {} }, onMessage: { addListener: function() {} }, postMessage: function() {} }; },
        sendMessage: function() {}
    },
    csi: function() { return {}; },
    loadTimes: function() {
        return {
            commitLoadTime: Date.now() / 1000 - Math.random() * 2,
            connectionInfo: 'http/1.1',
            finishDocumentLoadTime: Date.now() / 1000 - Math.random(),
            finishLoadTime: Date.now() / 1000,
            firstPaintAfterLoadTime: 0,
            firstPaintTime: Date.now() / 1000 - Math.random() * 1.5,
            navigationType: 'Other',
            npnNegotiatedProtocol: 'unknown',
            requestTime: Date.now() / 1000 - Math.random() * 3,
            startLoadTime: Date.now() / 1000 - Math.random() * 2.5,
            wasAlternateProtocolAvailable: false,
            wasFetchedViaSpdy: false,
            wasNpnNegotiated: false
        };
    }
};

// 10. 隐藏 Automation 相关属性
Object.defineProperty(navigator, 'automation', {
    get: () => undefined,
    configurable: true
});

// 11. 修复 iframe contentWindow 检测
const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
    get: function() {
        const window = originalContentWindow.get.call(this);
        if (window) {
            try {
                Object.defineProperty(window.navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
            } catch (e) {
                // 跨域 iframe 无法修改
            }
        }
        return window;
    }
});

console.log('[Stealth] DrissionPage anti-detection scripts injected');
"""

DRISSIONPAGE_ADVANCED_SCRIPT = """
// ========== DrissionPage 高级反检测脚本 ==========

// Canvas 指纹噪声
const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    const context = this.getContext('2d');
    if (context) {
        try {
            const imageData = context.getImageData(0, 0, this.width, this.height);
            const data = imageData.data;
            for (let i = 0; i < data.length; i += 4) {
                if (Math.random() < 0.005) {
                    data[i] = Math.max(0, Math.min(255, data[i] + Math.floor(Math.random() * 2)));
                    data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + Math.floor(Math.random() * 2)));
                    data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + Math.floor(Math.random() * 2)));
                }
            }
            context.putImageData(imageData, 0, 0);
        } catch (e) {}
    }
    return originalToDataURL.apply(this, arguments);
};

// WebGL 指纹伪造
if (window.WebGLRenderingContext) {
    const getParameterProxyHandler = {
        apply: function(target, thisArg, args) {
            const param = args[0];
            if (param === 37445) return 'Google Inc. (NVIDIA)';
            if (param === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
            return target.apply(thisArg, args);
        }
    };
    
    const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = new Proxy(originalGetParameter, getParameterProxyHandler);
}

// AudioContext 指纹噪声
if (window.AudioContext || window.webkitAudioContext) {
    const OriginalAudioContext = window.AudioContext || window.webkitAudioContext;
    const proxyAudioContext = new Proxy(OriginalAudioContext, {
        construct(target, args) {
            const ctx = new target(...args);
            const originalCreateOscillator = ctx.createOscillator.bind(ctx);
            ctx.createOscillator = function() {
                const oscillator = originalCreateOscillator();
                const originalFrequency = oscillator.frequency;
                Object.defineProperty(oscillator, 'frequency', {
                    get() {
                        return {
                            value: originalFrequency.value + (Math.random() * 0.0001 - 0.00005),
                            setValueAtTime: originalFrequency.setValueAtTime.bind(originalFrequency)
                        };
                    }
                });
                return oscillator;
            };
            return ctx;
        }
    });
    window.AudioContext = proxyAudioContext;
    if (window.webkitAudioContext) {
        window.webkitAudioContext = proxyAudioContext;
    }
}

console.log('[Stealth] DrissionPage advanced anti-detection scripts injected');
"""


def get_drissionpage_stealth_script(level: str = 'basic') -> str:
    """
    根据反检测级别获取 DrissionPage 脚本组合
    
    Args:
        level: 'none' | 'basic' | 'advanced'
        
    Returns:
        组合后的脚本字符串
    """
    if level == 'none':
        return ''
    
    scripts = [DRISSIONPAGE_STEALTH_SCRIPT]
    
    if level == 'advanced':
        scripts.append(DRISSIONPAGE_ADVANCED_SCRIPT)
    
    return '\n\n'.join(scripts)
