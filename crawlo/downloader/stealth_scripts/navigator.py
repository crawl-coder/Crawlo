#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Navigator 反检测脚本

隐藏浏览器自动化标识：
- 隐藏 navigator.webdriver
- 伪造 navigator.plugins
- 伪造 navigator.languages
- 隐藏 Playwright 特有标识
"""

NAVIGATOR_STEALTH_SCRIPT = """
// ========== Navigator 反检测 ==========

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

console.log('[Stealth] Navigator anti-detection scripts injected');
"""
