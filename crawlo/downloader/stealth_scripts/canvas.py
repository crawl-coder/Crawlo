#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Canvas 指纹噪声脚本

通过在 Canvas 绘制时添加噪声，
防止被 Canvas 指纹技术追踪。
"""

CANVAS_STEALTH_SCRIPT = """
// ========== Canvas 指纹噪声 ==========

// 1. 修改 CanvasRenderingContext2D 原型方法
const originalGetContext = HTMLCanvasElement.prototype.getContext;

HTMLCanvasElement.prototype.getContext = function(type, attributes) {
    const context = originalGetContext.call(this, type, attributes);
    
    if (!context) {
        return context;
    }
    
    // 对 2D Canvas 注入噪声
    if (type === '2d') {
        injectCanvasNoise(context, this);
    }
    
    return context;
};

// 2. Canvas 噪声注入函数
function injectCanvasNoise(ctx, canvas) {
    // 保存原始方法
    const originalFillText = ctx.fillText.bind(ctx);
    const originalStrokeText = ctx.strokeText.bind(ctx);
    const originalDrawImage = ctx.drawImage.bind(ctx);
    
    // 生成噪声偏移量
    const getNoiseOffset = () => Math.random() * 0.5 - 0.25;  // -0.25 到 0.25 的随机偏移
    
    // 重写 fillText
    ctx.fillText = function(text, x, y, maxWidth) {
        const noiseX = getNoiseOffset();
        const noiseY = getNoiseOffset();
        
        if (maxWidth) {
            return originalFillText(text, x + noiseX, y + noiseY, maxWidth);
        }
        return originalFillText(text, x + noiseX, y + noiseY);
    };
    
    // 重写 strokeText
    ctx.strokeText = function(text, x, y, maxWidth) {
        const noiseX = getNoiseOffset();
        const noiseY = getNoiseOffset();
        
        if (maxWidth) {
            return originalStrokeText(text, x + noiseX, y + noiseY, maxWidth);
        }
        return originalStrokeText(text, x + noiseX, y + noiseY);
    };
}

// 3. 添加 AudioContext 指纹噪声
if (window.AudioContext || window.webkitAudioContext) {
    const OriginalAudioContext = window.AudioContext || window.webkitAudioContext;
    
    const proxyAudioContext = new Proxy(OriginalAudioContext, {
        construct(target, args) {
            const ctx = new target(...args);
            
            // 代理 createOscillator
            const originalCreateOscillator = ctx.createOscillator.bind(ctx);
            ctx.createOscillator = function() {
                const oscillator = originalCreateOscillator();
                const originalFrequency = oscillator.frequency;
                
                // 添加微小的频率噪声
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

// 4. 修改 Canvas toBlob 方法
const originalToBlob = HTMLCanvasElement.prototype.toBlob;
HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
    // 添加像素级噪声
    const ctx = originalGetContext.call(this, '2d');
    
    if (ctx) {
        try {
            const imageData = ctx.getImageData(0, 0, this.width, this.height);
            const data = imageData.data;
            
            // 添加微小噪声（人眼不可见，但会影响指纹）
            for (let i = 0; i < data.length; i += 4) {
                if (Math.random() < 0.005) {  // 0.5% 的像素
                    data[i] = Math.max(0, Math.min(255, data[i] + Math.floor(Math.random() * 2)));
                    data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + Math.floor(Math.random() * 2)));
                    data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + Math.floor(Math.random() * 2)));
                }
            }
            
            ctx.putImageData(imageData, 0, 0);
        } catch (e) {
            // 某些情况下无法修改（如跨域）
        }
    }
    
    return originalToBlob.call(this, callback, type, quality);
};

// 5. 修改 getImageData 方法
const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
CanvasRenderingContext2D.prototype.getImageData = function(x, y, width, height) {
    const imageData = originalGetImageData.call(this, x, y, width, height);
    
    // 添加噪声
    const data = imageData.data;
    for (let i = 0; i < data.length; i += 4) {
        // 对 alpha 通道添加噪声（最不明显）
        data[i + 3] = Math.max(0, Math.min(255, data[i + 3] + Math.floor(Math.random() * 3) - 1));
    }
    
    return imageData;
};

// 6. 隐藏字体指纹
const originalMeasureText = CanvasRenderingContext2D.prototype.measureText;
CanvasRenderingContext2D.prototype.measureText = function(text) {
    const metrics = originalMeasureText.call(this, text);
    
    // 添加微小噪声到测量结果
    const noise = Math.random() * 0.1 - 0.05;
    
    return {
        width: metrics.width + noise,
        actualBoundingBoxLeft: metrics.actualBoundingBoxLeft || 0,
        actualBoundingBoxRight: metrics.actualBoundingBoxRight || 0 + noise,
        actualBoundingBoxAscent: metrics.actualBoundingBoxAscent || 0,
        actualBoundingBoxDescent: metrics.actualBoundingBoxDescent || 0,
        fontBoundingBoxAscent: metrics.fontBoundingBoxAscent || 0,
        fontBoundingBoxDescent: metrics.fontBoundingBoxDescent || 0,
        emHeightAscent: metrics.emHeightAscent || 0,
        emHeightDescent: metrics.emHeightDescent || 0,
        hangingBaseline: metrics.hangingBaseline || 0,
        alphabeticBaseline: metrics.alphabeticBaseline || 0,
        ideographicBaseline: metrics.ideographicBaseline || 0
    };
};

console.log('[Stealth] Canvas anti-detection scripts injected');
"""
