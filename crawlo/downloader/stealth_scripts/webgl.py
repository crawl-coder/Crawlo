#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
WebGL 指纹伪造脚本

通过添加噪声修改 WebGL 指纹，
避免被指纹追踪技术识别。
"""

WEBGL_STEALTH_SCRIPT = """
// ========== WebGL 指纹伪造 ==========

// 1. 伪造 WebGL Renderer 和 Vendor
const getParameterProxyHandler = {
    apply: function(target, thisArg, args) {
        const param = args[0];
        const gl = thisArg;
        
        // UNMASKED_VENDOR_WEBGL
        if (param === 37445) {
            return 'Google Inc. (NVIDIA)';
        }
        // UNMASKED_RENDERER_WEBGL
        if (param === 37446) {
            return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
        }
        
        return target.apply(thisArg, args);
    }
};

// 2. 代理 WebGLRenderingContext.getParameter
if (window.WebGLRenderingContext) {
    const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = new Proxy(originalGetParameter, getParameterProxyHandler);
}

// 3. 代理 WebGL2RenderingContext.getParameter
if (window.WebGL2RenderingContext) {
    const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = new Proxy(originalGetParameter2, getParameterProxyHandler);
}

// 4. 添加指纹噪声
const originalGetExtension = WebGLRenderingContext.prototype.getExtension;
WebGLRenderingContext.prototype.getExtension = function(name) {
    const extension = originalGetExtension.call(this, name);
    
    if (extension && name === 'WEBGL_debug_renderer_info') {
        // 返回伪造的扩展信息
        return {
            UNMASKED_VENDOR_WEBGL: 37445,
            UNMASKED_RENDERER_WEBGL: 37446
        };
    }
    
    return extension;
};

// 5. 伪造 WebGL Shader 精度格式
const originalGetShaderPrecisionFormat = WebGLRenderingContext.prototype.getShaderPrecisionFormat;
WebGLRenderingContext.prototype.getShaderPrecisionFormat = function(shaderType, precisionType) {
    const format = originalGetShaderPrecisionFormat.call(this, shaderType, precisionType);
    
    if (format) {
        // 添加噪声
        return {
            precision: format.precision + Math.floor(Math.random() * 2),
            rangeMin: format.rangeMin,
            rangeMax: format.rangeMax
        };
    }
    
    return format;
};

// 6. 添加 toDataURL 噪声（影响 Canvas 指纹）
const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    // 检查是否为 WebGL Canvas
    const context = this.getContext('webgl') || this.getContext('webgl2') || this.getContext('experimental-webgl');
    
    if (context) {
        // 添加微小噪声
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = this.width;
        tempCanvas.height = this.height;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.drawImage(this, 0, 0);
        
        // 添加噪声（修改少量像素）
        const imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
        const data = imageData.data;
        
        for (let i = 0; i < data.length; i += 4) {
            // 对部分像素添加微小噪声
            if (Math.random() < 0.001) {  // 0.1% 的像素
                data[i] = Math.max(0, Math.min(255, data[i] + Math.floor(Math.random() * 3) - 1));     // R
                data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + Math.floor(Math.random() * 3) - 1)); // G
                data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + Math.floor(Math.random() * 3) - 1)); // B
            }
        }
        
        tempCtx.putImageData(imageData, 0, 0);
        return originalToDataURL.apply(tempCanvas, arguments);
    }
    
    return originalToDataURL.apply(this, arguments);
};

// 7. 隐藏 WebGL 扩展泄露的特征
const originalGetSupportedExtensions = WebGLRenderingContext.prototype.getSupportedExtensions;
WebGLRenderingContext.prototype.getSupportedExtensions = function() {
    const extensions = originalGetSupportedExtensions.call(this) || [];
    
    // 过滤掉可能泄露自动化特征的扩展
    return extensions.filter(ext => {
        return !ext.includes('WEBGL_debug_');
    });
};

console.log('[Stealth] WebGL anti-detection scripts injected');
"""
