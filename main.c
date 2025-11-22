#include <stdio.h>
#include <stdlib.h>
#include <string.h> 
#include <ctype.h>
#include <windows.h>
#define MAX_SIZE_IP_NUM	12
#define MAX_SIZE_IP_LEN 17
#define MAX_PORT_LEN 6 
#pragma comment(linker,"/manifestdependency:\"type='win32' name='Microsoft.Windows.Common-Controls' " \
    "version='6.0.0.0' processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'\"")

#pragma comment(linker,"/manifest:\"<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" \
    "<assembly xmlns='urn:schemas-microsoft-com:asm.v1' manifestVersion='1.0'>" \
    "  <compatibility xmlns='urn:schemas-microsoft-com:compatibility.v1'>" \
    "    <application>" \
    "      <supportedOS Id='{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}'/>" \
    "      <supportedOS Id='{1f676c76-80e1-4239-95bb-83d0f6d0da78}'/>" \
    "    </application>" \
    "  </compatibility>" \
    "</assembly>\"")

int is_ipv4_addr(char *ip);
int is_valid_port(const char* port_str);
void flush_input_buffer();
char *trim_whitespace(char *str);

int main() {
    char ip[32], ssh_input[MAX_PORT_LEN+2], cmd[256];
    char local_port[MAX_PORT_LEN+2] = "";
    char remote_host[32] = "";
    char remote_port[MAX_PORT_LEN+2] = "";
    char username[32] = "root";  // 默认用户名
    const char* default_ssh = "22";
    
    printf("本程序作用是简化SSH连接和端口映射命令\n");
    printf("by高粱NexT\n");
    printf("检测系统中...\n"); 
    
    OSVERSIONINFOEX osvi;
    ZeroMemory(&osvi, sizeof(OSVERSIONINFOEX));
    osvi.dwOSVersionInfoSize = sizeof(OSVERSIONINFOEX);

    if (GetVersionEx((OSVERSIONINFO*)&osvi)) {
        printf("检测到系统版本号: %d.%d (Build %d)\n",
               osvi.dwMajorVersion, osvi.dwMinorVersion, osvi.dwBuildNumber);

        if (osvi.dwMajorVersion == 10 && osvi.dwMinorVersion == 0) {
            if (osvi.dwBuildNumber >= 22000)
                {
				printf("√ 当前系统: Windows 11\n");
                printf("支持cmd ssh系统要求\n");}
            else
                {
				printf("√ 当前系统: Windows 10\n");
                printf("支持cmd ssh系统要求\n");}
        }
        else if (osvi.dwMajorVersion == 6 && osvi.dwMinorVersion == 3)
            {
			printf("√ 当前系统: Windows 8.1\n");
			printf("此版本不支持cmd ssh系统要求\n");
			return 0;} 
        else if (osvi.dwMajorVersion == 6 && osvi.dwMinorVersion == 2)
            {
			printf("√ 当前系统: Windows 8\n");
				printf("此版本不支持cmd ssh系统要求\n");
			return 0;} 
        else if (osvi.dwMajorVersion == 6 && osvi.dwMinorVersion == 1)
            {printf("√ 当前系统: Windows 7\n");
            	printf("此版本不支持cmd ssh系统要求\n");
			return 0;} 
        else if (osvi.dwMajorVersion == 6 && osvi.dwMinorVersion == 0)
            {printf("√ 当前系统: Windows Vista\n");
			printf("此版本不支持cmd ssh系统要求\n");
			return 0;} 
        else if (osvi.dwMajorVersion == 5 && osvi.dwMinorVersion == 1)
            {printf("√ 当前系统: Windows XP\n");
			printf("此版本不支持cmd ssh系统要求\n");
			return 0;} 
        else
            {printf("√ 当前系统: 其他 Windows 版本\n");
            return 0;}
    } else {
        {printf("? 无法获取系统版本信息\n");
        return 0;} 
    }
    
    // 获取用户名
    printf("请输入SSH用户名(默认root): ");
    fgets(username, sizeof(username), stdin);
    username[strcspn(username, "\n")] = '\0';
    // 如果用户只按了回车，默认root
    if(strlen(username) == 0) {
        strcpy(username, "root");
    }
    
    // 获取IP地址
    printf("请输入ssh的ip: ");
    fgets(ip, sizeof(ip), stdin);
    ip[strcspn(ip, "\n")] = '\0';
    
    if (is_ipv4_addr(ip) != 0) {
        printf("输入的IP地址无效，请重新运行程序并输入正确的IPv4地址\n");
        return 0;
    }
    
    printf("请输入ssh的端口号(一般默认为22): ");
    fgets(ssh_input, sizeof(ssh_input), stdin);
    ssh_input[strcspn(ssh_input, "\n")] = '\0';
    
    const char* ssh_port = (strlen(ssh_input) > 0) ? ssh_input : default_ssh;
    if (is_valid_port(ssh_port) != 0) {
        printf("端口号无效，请输入1-65535之间的数字\n");
        return 0;
    }

    printf("是否要进行端口映射(y/n): ");
    char port_map_choice;
    scanf(" %c", &port_map_choice);
    flush_input_buffer();  
    
    char local_port[MAX_PORT_LEN+2] = "";
    char remote_host[32] = "";

    char remote_port[MAX_PORT_LEN+2] = "";
    int port_forwarding = 0;

    if (port_map_choice == 'y' || port_map_choice == 'Y') {
        port_forwarding = 1;

        printf("请输入本地端口号: ");
        fgets(local_port, sizeof(local_port), stdin);
        local_port[strcspn(local_port, "\n")] = '\0';

        printf("请输入远程主机IP(默认使用服务器IP %s): ", ip);
        fgets(remote_host, sizeof(remote_host), stdin);
        remote_host[strcspn(remote_host, "\n")] = '\0';
        if (strlen(remote_host) == 0) {
            strcpy(remote_host, ip);
        }

        printf("请输入远程端口号: ");
        fgets(remote_port, sizeof(remote_port), stdin);
        remote_port[strcspn(remote_port, "\n")] = '\0';

        if (is_valid_port(local_port) != 0 || is_valid_port(remote_port) != 0) {
            printf("端口号无效，请输入1-65535之间的数字\n");
            return 0;
        }
#include <stdio.h>
#include <stdlib.h>
#include <string.h> 
#include <ctype.h>
#include <windows.h>
#define MAX_SIZE_IP_NUM	12
#define MAX_SIZE_IP_LEN 17
#define MAX_PORT_LEN 6 
#pragma comment(linker,"/manifestdependency:\"type='win32' name='Microsoft.Windows.Common-Controls' " \
    "version='6.0.0.0' processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'\"")

#pragma comment(linker,"/manifest:\"<?xml version='1.0' encoding='UTF-8' standalone='yes'?>" \
    "<assembly xmlns='urn:schemas-microsoft-com:asm.v1' manifestVersion='1.0'>" \
    "  <compatibility xmlns='urn:schemas-microsoft-com:compatibility.v1'>" \
    "    <application>" \
    "      <supportedOS Id='{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}'/>" \
    "      <supportedOS Id='{1f676c76-80e1-4239-95bb-83d0f6d0da78}'/>" \
    "    </application>" \
    "  </compatibility>" \
    "</assembly>\"")

int is_ipv4_addr(char *ip);
int is_valid_port(const char* port_str);
void flush_input_buffer();
char *trim_whitespace(char *str);
int build_port_mappings(const char *input, const char* default_remote_host, char *out_flags, size_t out_size);

int main() {
    char ip[32], ssh_input[MAX_PORT_LEN+2], cmd[256];
    char local_port[MAX_PORT_LEN+2] = "";
    char remote_host[32] = "";
    char remote_port[MAX_PORT_LEN+2] = "";
    char username[32] = "root";  // 默认用户名
    const char* default_ssh = "22";
    
    printf("本程序作用是简化SSH连接和端口映射命令\n");
    printf("by高粱NexT\n");
    printf("检测系统中...\n"); 
    
    OSVERSIONINFOEX osvi;
    ZeroMemory(&osvi, sizeof(OSVERSIONINFOEX));
    osvi.dwOSVersionInfoSize = sizeof(OSVERSIONINFOEX);

    if (GetVersionEx((OSVERSIONINFO*)&osvi)) {
        printf("检测到系统版本号: %d.%d (Build %d)\n",
               osvi.dwMajorVersion, osvi.dwMinorVersion, osvi.dwBuildNumber);

        if (osvi.dwMajorVersion == 10 && osvi.dwMinorVersion == 0) {
            if (osvi.dwBuildNumber >= 22000)
                {
				printf("√ 当前系统: Windows 11\n");
                printf("支持cmd ssh系统要求\n");}
            else
                {
				printf("√ 当前系统: Windows 10\n");
                printf("支持cmd ssh系统要求\n");}
        }
        else if (osvi.dwMajorVersion == 6 && osvi.dwMinorVersion == 3)
            {
			printf("√ 当前系统: Windows 8.1\n");
			printf("此版本不支持cmd ssh系统要求\n");
			return 0;} 
        else if (osvi.dwMajorVersion == 6 && osvi.dwMinorVersion == 2)
            {
			printf("√ 当前系统: Windows 8\n");
				printf("此版本不支持cmd ssh系统要求\n");
			return 0;} 
        else if (osvi.dwMajorVersion == 6 && osvi.dwMinorVersion == 1)
            {printf("√ 当前系统: Windows 7\n");
            	printf("此版本不支持cmd ssh系统要求\n");
			return 0;} 
        else if (osvi.dwMajorVersion == 6 && osvi.dwMinorVersion == 0)
            {printf("√ 当前系统: Windows Vista\n");
			printf("此版本不支持cmd ssh系统要求\n");
			return 0;} 
        else if (osvi.dwMajorVersion == 5 && osvi.dwMinorVersion == 1)
            {printf("√ 当前系统: Windows XP\n");
			printf("此版本不支持cmd ssh系统要求\n");
			return 0;} 
        else
            {printf("√ 当前系统: 其他 Windows 版本\n");
            return 0;}
    } else {
        {printf("? 无法获取系统版本信息\n");
        return 0;} 
    }
    
    // 获取用户名
    printf("请输入SSH用户名(默认root): ");
    fgets(username, sizeof(username), stdin);
    username[strcspn(username, "\n")] = '\0';
    // 如果用户只按了回车，默认root
    if(strlen(username) == 0) {
        strcpy(username, "root");
    }
    
    // 获取IP地址
    printf("请输入ssh的ip: ");
    fgets(ip, sizeof(ip), stdin);
    ip[strcspn(ip, "\n")] = '\0';
    
    if (is_ipv4_addr(ip) != 0) {
        printf("输入的IP地址无效，请重新运行程序并输入正确的IPv4地址\n");
        return 0;
    }
    
    printf("请输入ssh的端口号(一般默认为22): ");
    fgets(ssh_input, sizeof(ssh_input), stdin);
    ssh_input[strcspn(ssh_input, "\n")] = '\0';
    
    const char* ssh_port = (strlen(ssh_input) > 0) ? ssh_input : default_ssh;
    if (is_valid_port(ssh_port) != 0) {
        printf("端口号无效，请输入1-65535之间的数字\n");
        return 0;
    }

    printf("是否要进行端口映射(y/n): ");
    char port_map_choice;
    scanf(" %c", &port_map_choice);
    flush_input_buffer();  
    
    int port_forwarding = 0;

    if (port_map_choice == 'y' || port_map_choice == 'Y') {
        port_forwarding = 1;

        printf("请输入本地端口号: ");
        fgets(local_port, sizeof(local_port), stdin);
        local_port[strcspn(local_port, "\n")] = '\0';

        printf("请输入远程主机IP(默认使用服务器IP %s): ", ip);
        fgets(remote_host, sizeof(remote_host), stdin);
        remote_host[strcspn(remote_host, "\n")] = '\0';
        if (strlen(remote_host) == 0) {
            strcpy(remote_host, ip);
        }

        printf("请输入远程端口号: ");
        fgets(remote_port, sizeof(remote_port), stdin);
        remote_port[strcspn(remote_port, "\n")] = '\0';

        // Validation for individual ports is now handled by build_port_mappings
        // is_valid_port can still be used for single port validation if needed elsewhere
    }
    else if (!(port_map_choice == 'n' || port_map_choice == 'N')) {
        printf("无效选择，请输入'y'或'n'\n");
        return 0;
    }

    // 构造并执行 ssh 命令
    if (port_forwarding) {
        char mapping_input[512];
        char ssh_flags[2048];
        
        // Construct the mapping string: local:host:remote
        snprintf(mapping_input, sizeof(mapping_input), "%s:%s:%s", local_port, remote_host, remote_port);
        
        if (build_port_mappings(mapping_input, remote_host, ssh_flags, sizeof(ssh_flags)) != 0) {
            printf("端口映射构建失败，请检查端口范围是否匹配 (例如 80-82 对应 80-82)\n");
            return 0;
        }
        
        snprintf(cmd, sizeof(cmd), "ssh %s %s@%s -p %s", 
                ssh_flags, username, ip, ssh_port);
    } else {
        // 普通SSH连接命令
        snprintf(cmd, sizeof(cmd), "ssh %s@%s -p %s", username, ip, ssh_port);
    }
    
    printf("正在连接...\n");
    printf("执行命令: %s\n", cmd);
    int result = system(cmd);
    
    if (result != 0) {
        printf("连接ssh终端失败请查询服务器or本机配置%d\n", result);
    }

    return 0;
}

// 验证IPv4地址合法性
int is_ipv4_addr(char *ip)
{
    if (ip == NULL || ip[0] == '\0') {
        return -1;
    }

    for (int i = 0; i < strlen(ip); i++) {
        if ((ip[i] != '.') && (ip[i] < '0' || ip[i] > '9')) {
            return -1;
        }
    }

    int dot_count = 0;
    for (int i = 0; i < strlen(ip); i++) {
        if (ip[i] == '.') {
            dot_count++;
            if (dot_count > 3 || (i > 0 && ip[i-1] == '.')) {
                return -1;
            }
        }
    }
    if (dot_count != 3) {
        return -1;
    }

    int ip_num[4] = {0};
    char ip_s[4][4];
    memset(ip_s, 0, sizeof(ip_s));

    if (sscanf(ip, "%3[^.].%3[^.].%3[^.].%3s", ip_s[0], ip_s[1], ip_s[2], ip_s[3]) != 4) {
        return -1;
    }

    for (int i = 0; i < 4; i++) {
        if (strlen(ip_s[i]) == 0 || (ip_s[i][0] == '0' && strlen(ip_s[i]) > 1)) {
            return -1;
        }
        
        ip_num[i] = atoi(ip_s[i]);
        if (ip_num[i] < 0 || ip_num[i] > 255) {
            return -1;
        }
    }

    return 0;
}

// 验证端口号合法性 (支持单个端口或范围 a-b)
int is_valid_port(const char* port_str) {
    if (port_str == NULL || strlen(port_str) == 0) {
        return -1;
    }
    
    // Check for range format
    const char *hyphen = strchr(port_str, '-');
    if (hyphen) {
        int start, end;
        if (sscanf(port_str, "%d-%d", &start, &end) != 2) return -1;
        if (start < 1 || start > 65535) return -1;
        if (end < 1 || end > 65535) return -1;
        if (start > end) return -1;
        return 0;
    }
    
    // 检查是否只包含数字
    for (size_t i = 0; i < strlen(port_str); i++) {
        if (!isdigit((unsigned char)port_str[i])) {
            return -1;
        }
    }
    
    // 检查是否在有效范围内(1-65535)
    int port = atoi(port_str);
    if (port < 1 || port > 65535) {
        return -1;
    }
    
    return 0;
}

// 清除输入缓冲区
void flush_input_buffer() {
    int c;
    while ((c = getchar()) != '\n' && c != EOF);
}

// 去除字符串首尾空白
char *trim_whitespace(char *str) {
    char *end;
    // trim leading
    while(isspace((unsigned char)*str)) str++;
    if(*str == 0) return str;
    // trim trailing
    end = str + strlen(str) - 1;
    while(end > str && isspace((unsigned char)*end)) end--;
    end[1] = '\0';
    return str;
}

// 简单解析映射，支持逗号分隔多个条目，条目格式：local:remote_host:remote OR local:remote
// 当 remote_host 省略时，使用 default_remote_host
// 返回0成功，-1失败
int build_port_mappings(const char *input, const char* default_remote_host, char *out_flags, size_t out_size) {
    if (input == NULL || strlen(input) == 0) {
        return -1;
    }
    char buf[512];
    strncpy(buf, input, sizeof(buf)-1);
    buf[sizeof(buf)-1] = '\0';

    out_flags[0] = '\0';
    size_t used = 0;

    char *tok = strtok(buf, ",");
    int total_flags = 0;
    while (tok != NULL) {
        char *part = trim_whitespace(tok);
        if (strlen(part) == 0) { tok = strtok(NULL, ","); continue; }

        // split by ':' into up to 3 parts
        char *p1 = NULL, *p2 = NULL, *p3 = NULL;
        char local_s[64] = "", host_s[128] = "", remote_s[64] = "";
        char tmp[256];
        strncpy(tmp, part, sizeof(tmp)-1);
        tmp[sizeof(tmp)-1] = '\0';

        char *c1 = strchr(tmp, ':');
        if (c1 == NULL) return -1;
        *c1 = '\0'; p1 = tmp;
        char *rest = c1 + 1;
        char *c2 = strchr(rest, ':');
        if (c2 != NULL) {
            *c2 = '\0'; p2 = rest; p3 = c2 + 1;
        } else {
            p2 = NULL; p3 = rest;
        }

        strncpy(local_s, p1, sizeof(local_s)-1); local_s[sizeof(local_s)-1] = '\0';
        if (p2) { strncpy(host_s, p2, sizeof(host_s)-1); host_s[sizeof(host_s)-1] = '\0'; }
        else { strncpy(host_s, default_remote_host, sizeof(host_s)-1); host_s[sizeof(host_s)-1] = '\0'; }
        strncpy(remote_s, p3, sizeof(remote_s)-1); remote_s[sizeof(remote_s)-1] = '\0';

        // 支持范围 a-b
        int l_start = 0, l_end = 0, r_start = 0, r_end = 0;
        int l_is_range = 0, r_is_range = 0;
        if (strchr(local_s, '-') != NULL) {
            if (sscanf(local_s, "%d-%d", &l_start, &l_end) != 2) return -1;
            l_is_range = 1;
        } else {
            l_start = atoi(local_s); l_end = l_start;
        }
        if (strchr(remote_s, '-') != NULL) {
            if (sscanf(remote_s, "%d-%d", &r_start, &r_end) != 2) return -1;
            r_is_range = 1;
        } else {
            r_start = atoi(remote_s); r_end = r_start;
        }

        int l_count = l_end - l_start + 1;
        int r_count = r_end - r_start + 1;
        if (l_count <= 0 || r_count <= 0) return -1;
        
        // 逻辑修复：不允许 单个本地端口 -> 多个远程端口 (会导致绑定冲突)
        if (!l_is_range && r_is_range) return -1;
        
        if (l_is_range && r_is_range && l_count != r_count) return -1; // require matching lengths

        int items = l_is_range ? l_count : r_count;
        if (items <= 0) items = 1;

        for (int i = 0; i < items; i++) {
            int l_val = l_start + (l_is_range ? i : 0);
            int r_val = r_start + (r_is_range ? i : 0);
            char flag[128];
            int n = snprintf(flag, sizeof(flag), "-L %d:%s:%d", l_val, host_s, r_val);
            if (n <= 0) return -1;
            if (used + n + 2 >= out_size) return -1;
            if (used > 0) { out_flags[used++] = ' '; out_flags[used] = '\0'; }
            strcpy(out_flags + used, flag);
            used += n;
            total_flags++;
            if (total_flags >= 256) break; // Increased limit
        }

        tok = strtok(NULL, ",");
    }
    if(total_flags == 0) return -1;
    return 0;
}