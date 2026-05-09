/*
 * ============================================================
 *  DRAGON REACTION GAME — Serveur
 *
 *  Concepts démontrés :
 *    - Threads POSIX (pthread)
 *    - Mutex  (verrou_jeu)  →  évite la Race Condition
 *    - Sockets TCP          →  communication réseau
 *
 *  Compiler : gcc server.c -o server -lpthread
 *  Lancer   : ./server
 * ============================================================
 *
 *  ARCHITECTURE :
 *
 *   Thread générateur  ──┐
 *                        ├──► verrou_jeu (Mutex) ◄── variables partagées
 *   Thread joueur 1   ──┤        lettre_active         faim / humeur
 *   Thread joueur 2   ──┘
 *
 *  Race Condition : les threads joueurs reçoivent le même événement
 *  et répondent en même temps. Le Mutex garantit que le premier
 *  qui entre dans la section critique gagne les points et efface
 *  lettre_active. Le second trouve lettre_active vide → trop lent.
 * ============================================================
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <time.h>

#define PORT        5555
#define MAX_JOUEURS 4

/* ─── Structure d'un joueur ─── */
typedef struct {
    int  socket;
    char nom[50];
    int  score;
} Joueur;

/* ─────────────────────────────────────────────────────────── */
/*  VARIABLES PARTAGÉES — protégées par verrou_jeu             */
/* ─────────────────────────────────────────────────────────── */
Joueur joueurs[MAX_JOUEURS];
int nb_joueurs   = 0;
int nb_max       = 0;

int  faim          = 100;  /* santé faim  du dragon : 0..100 */
int  humeur        = 100;  /* santé humeur du dragon : 0..100 */
int  jeu_termine   = 0;    /* 1 = fin de partie              */
char lettre_active = ' ';  /* 'f', 'h', ou ' ' (rien)       */

/* LE MUTEX : un seul thread à la fois peut modifier ce qui est au-dessus */
pthread_mutex_t verrou_jeu = PTHREAD_MUTEX_INITIALIZER;


/* ─────────────────────────────────────────────────────────── */
/*  Envoie un message à tous les joueurs + affiche au serveur  */
/* ─────────────────────────────────────────────────────────── */
void diffuser(const char *msg)
{
    for (int i = 0; i < nb_joueurs; i++)
        send(joueurs[i].socket, msg, strlen(msg), 0);
    printf("%s", msg);
    fflush(stdout);
}


/* ─────────────────────────────────────────────────────────── */
/*  RÉSUMÉ FINAL                                               */
/*  Appelé depuis main() APRÈS que tous les threads joueurs    */
/*  sont terminés → aucune concurrence, pas besoin du mutex.   */
/* ─────────────────────────────────────────────────────────── */
void afficher_resultats(void)
{
    /* Tri à bulles : meilleur score en premier */
    for (int i = 0; i < nb_joueurs - 1; i++)
        for (int j = 0; j < nb_joueurs - 1 - i; j++)
            if (joueurs[j].score < joueurs[j+1].score) {
                Joueur tmp   = joueurs[j];
                joueurs[j]   = joueurs[j+1];
                joueurs[j+1] = tmp;
            }

    char buf[256];
    const char *places[] = {"1er", "2eme", "3eme", "   "};

    diffuser("\n======= CLASSEMENT FINAL =======\n");
    for (int i = 0; i < nb_joueurs; i++) {
        const char *p = (i < 3) ? places[i] : places[3];
        sprintf(buf, "  %s  %-20s  %d pts\n",
                p, joueurs[i].nom, joueurs[i].score);
        diffuser(buf);
    }
    sprintf(buf, "\nGAGNANT : %s avec %d points !\n",
            joueurs[0].nom, joueurs[0].score);
    diffuser(buf);
    diffuser("=================================\n");
    diffuser("\nFermeture dans 4 secondes...\n");

    sleep(4);   /* laisser les clients afficher le résumé avant la coupure */
}


/* ─────────────────────────────────────────────────────────── */
/*  THREAD GÉNÉRATEUR                                          */
/*  Toutes les 3-6 secondes :                                  */
/*    1. Diminue faim et humeur                                */
/*    2. Si l'un tombe à 0 → dragon mort → fin de partie      */
/*    3. Sinon, lance un événement aléatoire 'f' ou 'h'        */
/* ─────────────────────────────────────────────────────────── */
void *thread_generateur(void *arg)
{
    (void)arg;
    char buf[128];

    while (1) {
        sleep((rand() % 4) + 3);   /* pause aléatoire 3..6 secondes */

        pthread_mutex_lock(&verrou_jeu);

        faim   -= 10;
        humeur -= 10;

        /* Dragon mort ? */
        if (faim <= 0 || humeur <= 0) {
            jeu_termine = 1;
            pthread_mutex_unlock(&verrou_jeu);
            break;
        }

        /* Lancer un événement si aucun n'est déjà en attente */
        if (lettre_active == ' ') {
            if (rand() % 2 == 0) {
                lettre_active = 'f';
                sprintf(buf, "\n[!] DRAGON A FAIM !   Tapez 'f'  "
                             "[faim:%d humeur:%d]\n", faim, humeur);
            } else {
                lettre_active = 'h';
                sprintf(buf, "\n[!] DRAGON S'ENNUIE ! Tapez 'h'  "
                             "[faim:%d humeur:%d]\n", faim, humeur);
            }
            diffuser(buf);
        }

        pthread_mutex_unlock(&verrou_jeu);
    }

    return NULL;
}


/* ─────────────────────────────────────────────────────────── */
/*  THREAD JOUEUR                                              */
/*                                                             */
/*  ► RACE CONDITION ICI :                                     */
/*    Si deux joueurs tapent au même moment, leurs messages    */
/*    arrivent à quelques ms d'intervalle.                     */
/*    Sans mutex → les deux pourraient gagner les points.      */
/*    Avec mutex → le premier verrouille, prend les points,    */
/*    remet lettre_active = ' ', déverrouille.                 */
/*    Le second arrive, voit ' ' → pénalisé (trop lent).       */
/* ─────────────────────────────────────────────────────────── */
void *gerer_joueur(void *arg)
{
    int  id = *(int *)arg;
    char buffer[256];
    char reponse[256];

    while (!jeu_termine) {

        memset(buffer, 0, sizeof(buffer));
        /* Bloquant : attend que le joueur tape quelque chose */
        if (recv(joueurs[id].socket, buffer, sizeof(buffer) - 1, 0) <= 0)
            break;  /* socket fermé → on sort */

        if (jeu_termine) break;

        char touche = buffer[0];

        /* ══ DEBUT SECTION CRITIQUE ══════════════════════════ */
        pthread_mutex_lock(&verrou_jeu);

        if (!jeu_termine) {

            if ((lettre_active == 'f' && touche == 'f') ||
                (lettre_active == 'h' && touche == 'h'))
            {
                /* ✅ Bonne lettre + premier arrivé */
                joueurs[id].score += 10;
                if (touche == 'f')
                    faim   = (faim   + 20 > 100) ? 100 : faim   + 20;
                else
                    humeur = (humeur + 20 > 100) ? 100 : humeur + 20;

                lettre_active = ' ';   /* consommé : les autres arriveront trop tard */

                sprintf(reponse, "[OK] %s le plus rapide ! (+10 pts) | Score: %d\n",
                        joueurs[id].nom, joueurs[id].score);
                diffuser(reponse);

            } else if (lettre_active != ' ') {
                /* ❌ Mauvaise lettre */
                joueurs[id].score -= 5;
                if (joueurs[id].score < 0) joueurs[id].score = 0;

                sprintf(reponse, "[X]  %s : mauvaise lettre ! (-5 pts) | Score: %d\n",
                        joueurs[id].nom, joueurs[id].score);
                diffuser(reponse);

            } else {
                /* lettre_active == ' ' : trop lent ou spam */
                joueurs[id].score -= 2;
                if (joueurs[id].score < 0) joueurs[id].score = 0;

                sprintf(reponse, "[~]  %s trop lent ! (-2 pts) | Score: %d\n",
                        joueurs[id].nom, joueurs[id].score);
                diffuser(reponse);
            }
        }

        pthread_mutex_unlock(&verrou_jeu);
        /* ══ FIN SECTION CRITIQUE ════════════════════════════ */
    }

    return NULL;
}


/* ─────────────────────────────────────────────────────────── */
/*  MAIN                                                       */
/* ─────────────────────────────────────────────────────────── */
int main(void)
{
    int socket_serveur;
    struct sockaddr_in adresse;
    srand((unsigned)time(NULL));

    printf("===== DRAGON REACTION GAME =====\n\n");
    printf("Nombre de joueurs (1-%d) : ", MAX_JOUEURS);
    scanf("%d", &nb_max);
    getchar();
    if (nb_max < 1 || nb_max > MAX_JOUEURS) nb_max = 2;

    /* ── Création du socket serveur ── */
    socket_serveur = socket(AF_INET, SOCK_STREAM, 0);
    int opt = 1;
    setsockopt(socket_serveur, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    adresse.sin_family      = AF_INET;
    adresse.sin_addr.s_addr = INADDR_ANY;
    adresse.sin_port        = htons(PORT);
    bind(socket_serveur, (struct sockaddr *)&adresse, sizeof(adresse));
    listen(socket_serveur, nb_max);

    printf("En attente de %d joueur(s) sur le port %d...\n\n", nb_max, PORT);

    /* ── Connexion des joueurs ── */
    while (nb_joueurs < nb_max) {
        joueurs[nb_joueurs].socket = accept(socket_serveur, NULL, NULL);
        joueurs[nb_joueurs].score  = 0;

        send(joueurs[nb_joueurs].socket, "Ton pseudo : ", 13, 0);
        char tmp[50] = {0};
        recv(joueurs[nb_joueurs].socket, tmp, 49, 0);
        tmp[strcspn(tmp, "\r\n")] = '\0';
        strncpy(joueurs[nb_joueurs].nom, tmp, 49);

        printf("  >> %s est connecte.\n", joueurs[nb_joueurs].nom);
        nb_joueurs++;
    }

    diffuser("\n=== QUE LE PLUS RAPIDE GAGNE ! ===\n\n");

    /* ── Lancement des threads ── */
    pthread_t thread_gen;
    pthread_t threads_j[MAX_JOUEURS];
    int ids[MAX_JOUEURS];

    pthread_create(&thread_gen, NULL, thread_generateur, NULL);
    for (int i = 0; i < nb_max; i++) {
        ids[i] = i;
        pthread_create(&threads_j[i], NULL, gerer_joueur, &ids[i]);
    }

    /* ── Attendre la mort du dragon ── */
    pthread_join(thread_gen, NULL);

    /*
     * Le générateur est terminé (jeu_termine == 1).
     * On ferme les sockets pour débloquer les recv()
     * des threads joueurs qui attendent une frappe.
     */
    for (int i = 0; i < nb_max; i++)
        shutdown(joueurs[i].socket, SHUT_RDWR);

    /* Attendre que tous les threads joueurs sortent */
    for (int i = 0; i < nb_max; i++)
        pthread_join(threads_j[i], NULL);

    /*
     * ICI : aucun thread ne tourne → aucune concurrence.
     * On envoie le résumé final sans risque.
     */
    diffuser("\n*** LE DRAGON EST MORT ! ***\n");
    afficher_resultats();

    /* ── Fermeture propre ── */
    for (int i = 0; i < nb_max; i++) close(joueurs[i].socket);
    close(socket_serveur);
    return 0;
}
