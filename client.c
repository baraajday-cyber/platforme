/*
 * ============================================================
 *  DRAGON REACTION GAME — Client
 *
 *  Compiler : gcc client.c -o client -lpthread
 *  Lancer   : ./client
 *
 *  Le client utilise 2 threads :
 *   - thread d'écoute  → reçoit et affiche les messages du serveur
 *   - thread principal → lit le clavier et envoie les frappes
 * ============================================================
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>

/* Partagé entre les deux threads : 0 = fin de partie */
static volatile int connecte = 1;

/* Socket global pour que le thread d'écoute puisse le lire */
static int sock_global = -1;


/* ─────────────────────────────────────────────────────────── */
/*  THREAD D'ÉCOUTE                                            */
/*  Reçoit les messages du serveur et les affiche.             */
/*  Quand le serveur ferme la connexion, met connecte = 0      */
/*  et ferme stdin pour débloquer le fgets() du thread         */
/*  principal (qui attend sinon indéfiniment).                 */
/* ─────────────────────────────────────────────────────────── */
void *ecouter_serveur(void *arg)
{
    (void)arg;
    char buf[512];

    while (connecte) {
        memset(buf, 0, sizeof(buf));
        int n = recv(sock_global, buf, sizeof(buf) - 1, 0);

        if (n <= 0) {
            /* Serveur fermé → signaler la fin */
            connecte = 0;
            /*
             * Fermer stdin pour débloquer fgets() dans le thread
             * principal (sinon il attend une frappe clavier pour
             * toujours et le programme ne quitte jamais).
             */
            fclose(stdin);
            break;
        }

        printf("%s", buf);
        fflush(stdout);
    }

    return NULL;
}


/* ─────────────────────────────────────────────────────────── */
/*  MAIN                                                       */
/* ─────────────────────────────────────────────────────────── */
int main(void)
{
    struct sockaddr_in adresse;
    char ip[50];
    char message[256];
    pthread_t thread_ecoute;

    printf("IP du serveur (ex: 127.0.0.1) : ");
    scanf("%49s", ip);
    getchar();

    /* ── Connexion au serveur ── */
    sock_global = socket(AF_INET, SOCK_STREAM, 0);
    adresse.sin_family = AF_INET;
    adresse.sin_port   = htons(5555);
    inet_pton(AF_INET, ip, &adresse.sin_addr);

    if (connect(sock_global, (struct sockaddr *)&adresse, sizeof(adresse)) < 0) {
        perror("Connexion impossible");
        return 1;
    }

    /* ── Réception et réponse à la demande de pseudo ── */
    char question[100] = {0};
    recv(sock_global, question, sizeof(question) - 1, 0);
    printf("%s", question);
    fflush(stdout);

    fgets(message, 50, stdin);
    send(sock_global, message, strlen(message), 0);

    /* ── Lancement du thread d'écoute ── */
    pthread_create(&thread_ecoute, NULL, ecouter_serveur, NULL);

    printf("[Tapez 'f' ou 'h' puis Entree quand le dragon agit]\n\n");

    /* ── Boucle principale : lire le clavier et envoyer ── */
    while (connecte) {
        memset(message, 0, sizeof(message));

        /* fgets se débloque quand stdin est fermé par le thread d'écoute */
        if (fgets(message, sizeof(message), stdin) == NULL) break;

        message[strcspn(message, "\r\n")] = '\0';

        if (strlen(message) > 0 && connecte)
            send(sock_global, message, strlen(message), 0);
    }

    /*
     * Attendre que le thread d'écoute ait affiché tous les
     * messages restants (résumé final inclus) avant de quitter.
     */
    pthread_join(thread_ecoute, NULL);

    printf("\nPartie terminee. A bientot !\n");
    close(sock_global);
    return 0;
}
