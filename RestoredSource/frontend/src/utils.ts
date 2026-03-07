/**
 * 比较两个版本号字符串
 * @param v1 远程版本号 (e.g., "1.0.1")
 * @param v2 本地版本号 (e.g., "1.0.0")
 * @returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal
 */
/**
 * 清理版本号字符串，移除所有非数字和小数点的字符
 * 例如: "v1.0.1" -> "1.0.1", "version 1.0.1" -> "1.0.1", "vv1.0.1" -> "1.0.1"
 */
export const cleanVersion = (v: string): string => {
    // 匹配第一个数字及其之后的内容，直到非版本号字符
    // 简单粗暴：只保留数字和点
    return v.replace(/[^0-9.]/g, '');
};

/**
 * 比较两个版本号字符串
 * @param v1 远程版本号 (e.g., "1.0.1")
 * @param v2 本地版本号 (e.g., "1.0.0")
 * @returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal
 */
export const compareVersions = (v1: string, v2: string): number => {
    const cleanV1 = cleanVersion(v1);
    const cleanV2 = cleanVersion(v2);
    
    const parts1 = cleanV1.split('.').map(Number);
    const parts2 = cleanV2.split('.').map(Number);
    
    const len = Math.max(parts1.length, parts2.length);
    
    for (let i = 0; i < len; i++) {
        const val1 = isNaN(parts1[i]) ? 0 : parts1[i];
        const val2 = isNaN(parts2[i]) ? 0 : parts2[i];
        
        if (val1 > val2) return 1;
        if (val1 < val2) return -1;
    }
    
    return 0;
};
