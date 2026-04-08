#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Chrome Runtime API 伪装脚本

伪造 Chrome DevTools Protocol (CDP) 相关特征，
避免被检测为自动化浏览器。
"""

CHROME_RUNTIME_SCRIPT = """
// ========== Chrome Runtime API 伪装 ==========

// 1. 伪造 window.cdc_adoQpoasnfa76pfcZLmcfl_Array
// 这是 Chrome DevTools 的特征变量
window.cdc_adoQpoasnfa76pfcZLmcfl_Array = Array;
window.cdc_adoQpoasnfa76pfcZLmcfl_Object = Object;
window.cdc_adoQpoasnfa76pfcZLmcfl_Promise = Promise;
window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy = Proxy;
window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol = Symbol;
window.cdc_adoQpoasnfa76pfcZLmcfl_JSON = JSON;
window.cdc_adoQpoasnfa76pfcZLmcfl_Math = Math;

// 2. 隐藏 CDP Runtime 特征
const originalArrayPrototype = Array.prototype;
const nativeArrayPush = originalArrayPrototype.push;

// 某些检测会检查数组方法是否被重写
if (!originalArrayPrototype.push.toString().includes('[native code]')) {
    Object.defineProperty(originalArrayPrototype.push, 'toString', {
        value: function() { return 'function push() { [native code] }'; },
        configurable: true
    });
}

// 3. 伪造 Notification 权限
if (window.Notification) {
    Object.defineProperty(Notification, 'permission', {
        get: () => 'default',
        configurable: true
    });
}

// 4. 隐藏 Automation Extensions
const originalAddEventListener = EventTarget.prototype.addEventListener;
EventTarget.prototype.addEventListener = function(type, listener, options) {
    // 过滤掉自动化相关的监听器
    if (type === 'webdriver-evaluate' || type === 'webdriver-script') {
        return;
    }
    return originalAddEventListener.call(this, type, listener, options);
};

// 5. 伪造 Connection API
if (navigator.connection) {
    Object.defineProperty(navigator.connection, 'rtt', {
        get: () => 50 + Math.floor(Math.random() * 100),  // 50-150ms
        configurable: true
    });
    
    Object.defineProperty(navigator.connection, 'downlink', {
        get: () => 10 + Math.random() * 5,  // 10-15 Mbps
        configurable: true
    });
    
    Object.defineProperty(navigator.connection, 'effectiveType', {
        get: () => '4g',
        configurable: true
    });
    
    Object.defineProperty(navigator.connection, 'saveData', {
        get: () => false,
        configurable: true
    });
}

// 6. 伪造 Screen 信息
Object.defineProperty(screen, 'colorDepth', {
    get: () => 24,
    configurable: true
});

Object.defineProperty(screen, 'pixelDepth', {
    get: () => 24,
    configurable: true
});

// 添加 availWidth/availHeight 噪声（避免完全一致）
const originalAvailWidth = screen.availWidth;
const originalAvailHeight = screen.availHeight;

Object.defineProperty(screen, 'availWidth', {
    get: () => originalAvailWidth || screen.width,
    configurable: true
});

Object.defineProperty(screen, 'availHeight', {
    get: () => (originalAvailHeight || screen.height) - 40,  // 减去任务栏高度
    configurable: true
});

// 7. 隐藏 Automation Controller 特征
delete navigator.__proto__.controller;

// 8. 伪造 Font Access API
if (!navigator.fonts) {
    Object.defineProperty(navigator, 'fonts', {
        get: () => ({
            check: (font) => true,
            ready: Promise.resolve()
        }),
        configurable: true
    });
}

console.log('[Stealth] Chrome Runtime anti-detection scripts injected');
"""
