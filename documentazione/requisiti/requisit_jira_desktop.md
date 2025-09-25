Documento di Requisiti Software: Jira Time Tracker Desktop
1. Introduzione e Obiettivi del Progetto
1.1. Scopo del Progetto: Creare un'applicazione desktop che semplifichi e ottimizzi il tracciamento del tempo e l'interazione con le issue di Jira, riducendo i cambi di contesto, migliorando la produttività e permettendo di associare note locali private a ciascuna issue.
1.2. Utenti di Riferimento: Sviluppatori software, analisti, team leader che necessitano di un modo rapido per consultare le Jira e registrare il proprio lavoro.
1.3. Obiettivi Misurabili: Ridurre del 30% il tempo speso per la registrazione dei worklog; Diminuire del 50% il numero di accessi all'interfaccia web di Jira per operazioni di routine (commenti, allegati).
2. Requisiti Funzionali
2.1. Configurazione Iniziale e Gestione delle Impostazioni
2.1.1. Configurazione Iniziale: Al primo avvio, all'utente verrà presentata una finestra di configurazione che richiede URL dell'istanza Jira e Personal Access Token (PAT).
* Dettaglio Convalida: La convalida avverrà tramite una chiamata API GET all'endpoint /rest/api/2/myself di Jira. In caso di errore (es. 401 Unauthorized, 403 Forbidden, errore di rete), verrà mostrato un messaggio di errore esplicito.
* JQL Predefinita Iniziale: La JQL predefinita iniziale sarà assignee = currentUser() AND resolution is EMPTY ORDER BY updated DESC.
2.1.2. Schermata di Impostazioni: Accessibile dalla taskbar, permetterà di modificare URL, PAT e JQL predefinita. Un pulsante "Salva" applicherà le modifiche.
2.1.3. Gestione Avanzata (nelle Impostazioni):
* Colori Stati Jira: L'utente potrà configurare colori di evidenziazione per specifici stati di Jira. L'interfaccia mostrerà una tabella con colonne "Nome Stato" (testo) e "Colore" (un selettore di colore). Per default, lo stato "Collaudo Negativo" sarà pre-configurato con il colore rosso (#E74C3C). Queste mappature verranno salvate localmente.
* Gestione Query JQL: L'utente potrà visualizzare la cronologia delle ultime 20 query JQL eseguite e salvare le più usate come "preferite", assegnando loro un'etichetta (es. "Le mie issue aperte"). Saranno disponibili pulsanti per salvare una query dalla cronologia ai preferiti o per eliminare voci da entrambe le liste.
* Impostazioni di Sincronizzazione:
* Sincronizzazione Automatica: Sarà presente una casella di controllo "Abilita sincronizzazione automatica dei dati (worklog, commenti, ecc.)".
* Comportamento di Default: Questa opzione sarà disattivata per impostazione predefinita.
* Logica: Se attiva, l'applicazione tenterà di inviare i dati a Jira non appena vengono accodati (es. premendo "Ferma" sul cronometro). Se disattivata, i dati verranno solo aggiunti alla coda locale e dovranno essere sincronizzati manualmente.
*  Impostazioni di Visualizzazione Griglia:
* Configurazione Colonne Tempo: L'utente potrà scegliere quali colonne di tempo visualizzare nella griglia tramite delle caselle di controllo:
* [x] Mostra Tempo Locale Tracciato (tempo in LocalTimeLog)
* [x] Mostra Tempo Remoto (tempo timespent da Jira)
* [ ] Mostra Tempo Totale (somma dei due)
* Per default, le prime due opzioni saranno attive.

2.2. Finestra Principale (Container)
Applicazione contenuta in una singola finestra ridimensionabile con controlli standard.
Taskbar superiore con pulsanti: "Griglia Jira", "Cronologia", "Jira Favorite", "Ultima Jira Attiva", "Impostazioni", e un'area di stato a destra.

2.2.1. Comportamento dei Pulsanti della Taskbar:
* "Griglia Jira": Mostra la vista griglia, applicando il filtro JQL definito nelle impostazioni o quello personalizzato dall'utente.
* "Cronologia": Mostra una vista a griglia con le ultime 100 issue aperte in dettaglio dall'utente, ordinate dalla più recente (basato sulla tabella ViewHistory).
* "Jira Favorite": Agisce come un toggle. Quando attivo, filtra la "Griglia Jira" mostrando solo le issue contrassegnate come preferite (tabella FavoriteJiras).
* "Ultima Jira Attiva": Apre la finestra di dettaglio per l'ultima issue su cui il cronometro è stato attivo. Se nessuna Jira è stata attiva, il pulsante è disabilitato.
2.2.2. Gestione delle Viste: Cliccando su un pulsante della taskbar ("Griglia Jira", "Cronologia", "Jira Favorite"), la vista centrale dell'applicazione si aggiornerà per mostrare il contenuto richiesto, ricaricando i dati se necessario e garantendo che i filtri e gli stati precedenti non interferiscano con la nuova vista.

2.2.3. Area di Stato e Notifiche (nella Taskbar):
* Icona di Sincronizzazione: Sarà presente un'icona (es. sync) che indicherà lo stato della sincronizzazione:
* Verde/Check: Tutti i dati sono sincronizzati.
* Giallo/In attesa: Ci sono operazioni in coda in attesa di essere sincronizzate.
* Blu/In rotazione: Sincronizzazione in corso.
* Rosso/Alert: Ci sono stati errori durante l'ultima sincronizzazione.
* Azione al Click: Cliccando questa icona, se ci sono operazioni in attesa o fallite, si avvierà una sincronizzazione manuale di tutta la coda. Se ci sono errori, aprirà la finestra di gestione errori (come definito in 4.5.2).
* Icona Notifiche: Sarà presente un'icona a forma di campanella (bell). Se ci sono nuove notifiche (es. nuovi commenti su issue seguite), mostrerà un badge numerico. Cliccando l'icona si aprirà un piccolo pannello a discesa con un elenco di link alle issue con aggiornamenti.

2.3. Vista Griglia (e Viste Simili come Cronologia/Favorite)
2.3.1.  Visualizzazione Dati: Griglia con colonne configurabili. Le colonne di default saranno: Icona Notifiche, Chiave Jira, Titolo, Stato, Tempo Locale, Tempo Remoto, pulsante Dettaglio, pulsante Favoriti.
* Le colonne "Tempo Locale" e "Tempo Remoto" saranno visibili in base alla configurazione nelle impostazioni (vedi 2.1.3).
* Evidenziazione Stato: Le righe della griglia avranno uno sfondo colorato (o un indicatore visivo) in base alle regole definite nelle impostazioni (vedi 2.1.3).
* Tempo Totale Dedicato: Mostrerà la somma del tempo registrato su Jira (timespent) più il tempo tracciato localmente (LocalTimeLog) e non ancora sincronizzato.
2.3.2. Funzionalità:
* Barra di ricerca: Filtra i risultati attualmente visibili nella griglia per chiave, titolo o descrizione.
* Filtro JQL Personalizzato: Sarà presente un campo di testo per la JQL. Questo campo avrà un menu a discesa che permetterà di selezionare rapidamente le query dalla cronologia o dai preferiti (vedi 2.1.3). Ogni JQL inserita manualmente verrà salvata nella cronologia.
* Ordinamento: Tutte le colonne sono ordinabili (ASC/DESC) cliccando sull'header.
2.3.3. Interazione Utente:
* Il doppio click su una riga aprirà la "Finestra Dettaglio Jira". su tutte le diverse griglie. All'apertura, la Jira Key e la data/ora corrente verranno salvate nella ViewHistory.
* Pulsante Favoriti: Un'icona a stella per aggiungere/rimuovere l'issue dalla lista dei preferiti locali.
* Pulsante Notifiche: Per ogni riga sarà presente un'icona a campanella (bell-outline/bell). Cliccando questa icona si aggiunge/rimuove l'issue dalla lista di quelle monitorate per nuovi commenti (tabella NotificationSubscriptions).
2.3.4. Fonte dei Dati e Paginazione:
* I risultati verranno caricati in blocchi da 100 issue. Verrà implementato lo "scroll infinito" fino a un massimo di 1000 issue per sessione, per evitare carichi eccessivi.
2.3.5. Comportamento all'Avvio: Dopo la configurazione iniziale, ad ogni avvio l'applicazione aprirà di default la vista "Griglia Jira".
2.4. Finestra Dettaglio Jira
2.4.1. Header: Chiave Jira, Titolo della Jira, Cronometro in tempo reale (hh:mm:ss) e Stato attuale della Jira.
2.4.2. Controlli Cronometro: Pulsanti: "Pausa", "Ferma", "Aggiungi Tempo Manualmente".
2.4.2.1. Logica di Registrazione Tempo:
* Pulsante "Ferma": Arresta il cronometro. Il tempo accumulato viene sempre salvato come una nuova voce nella tabella LocalWorklogHistory e aggiunto alla coda di sincronizzazione (SyncQueue) con stato "Pending".
* Se la sincronizzazione automatica è attiva (vedi 2.1.3), l'applicazione tenterà immediatamente di processare questa nuova voce della coda.
* Se la sincronizzazione automatica è disattivata, la voce rimarrà in coda finché non verrà avviata una sincronizzazione manuale.
* Pulsante "Aggiungi Tempo Manualmente": Apre una finestra modale per inserire tempo, data e commento. Alla conferma, crea una nuova voce in LocalWorklogHistory e la aggiunge alla SyncQueue. La logica segue lo stesso principio del pulsante "Ferma": la voce viene sempre accodata, ma la sincronizzazione immediata dipende dall'impostazione.
2.4.3. Sezione a Tab:
* Tab 1 - Dettagli (Default all'apertura): Mostra i campi principali della Jira (Descrizione, Tipo, Priorità, ecc.).
* Tab 2 - Cronologia Tempo Locale:
* Mostra una tabella di tutte le sessioni di tempo registrate da questa applicazione per la issue corrente.
* Le colonne saranno: "Data Inizio", "Durata", "Commento" (se presente), "Stato Sincronizzazione" (es. In attesa, Sincronizzato, Errore).
* Questa vista è popolata dalla tabella LocalWorklogHistory e fornisce una cronologia dettagliata del lavoro svolto.
* Tab 3 - Commenti: Visualizza commenti esistenti e permette di aggiungerne di nuovi.
* Tab 4 - Allegati: Visualizza allegati e permette di caricarne di nuovi o scaricare quelli esistenti.
* Tab 5 - Annotazioni Personali: Editor Markdown per note private salvate localmente, con interfaccia a tab verticali per più note.
2.5. Gestione Cronometri Multipli
Avviare un cronometro su una nuova Jira mette automaticamente in pausa il cronometro precedente. Il tempo accumulato viene salvato in LocalTimeLog per la Jira corrispondente.
2.6. Vista Minimizzata (Widget)
Alla minimizzazione, appare un widget "sempre in primo piano" con chiave Jira, cronometro e una combobox per passare rapidamente a una Jira preferita.
3. Requisiti di Integrazione con Jira
3.1. Autenticazione: Tramite Personal Access Token (PAT) dell'utente.
3.2. Compatibilità: Sviluppo basato su Jira Server / Data Center v9.10.2.
4. Requisiti Non Funzionali
4.1. Piattaforma di Destinazione: Windows (con potenziale espansione futura).
4.2. Performance: Caricamento griglia (prime 100 issue) < 5 secondi. Ricerca locale < 3 secondi.
4.3. Sicurezza: Il PAT sarà salvato tramite il gestore di credenziali del sistema operativo (es. keyring).
4.4. Gestione Dati Locali: Database SQLite locale nella cartella dati dell'utente (es. %APPDATA%\JiraTimeTracker).
4.5. Gestione degli Errori e Modalità Offline:
* Le operazioni di scrittura (worklog, commenti) vengono aggiunte a una "coda di sincronizzazione" locale (SyncQueue).
* L'app tenta di processare la coda periodicamente quando la connessione è disponibile.
* Un'icona di stato nella taskbar principale indicherà la presenza di errori di sincronizzazione, con una finestra di gestione per riprovare o eliminare le operazioni fallite.

4.5.1. Comportamento in Modalità Offline:
* Le operazioni di scrittura (worklog, commenti) vengono sempre aggiunte alla SyncQueue locale.
* Se la sincronizzazione automatica è attiva, l'app tenta di processare la coda automaticamente quando la connessione torna disponibile.
4.5.2. Interfaccia di Gestione Errori: L'icona di stato nella taskbar principale indicherà gli errori. Cliccando sull'icona si aprirà una finestra di gestione per riprovare o eliminare le operazioni fallite.
4.6. Servizio di Notifiche in Background
* Meccanismo di Controllo: L'applicazione eseguirà un processo in background ogni ora.
* Logica: Questo processo recupererà l'elenco delle issue dalla tabella NotificationSubscriptions. Per ciascuna issue, interrogherà l'API di Jira per ottenere i commenti più recenti e confronterà l'ID o la data dell'ultimo commento con l'ultimo stato noto.
* Generazione Notifica: Se vengono rilevati nuovi commenti, l'icona della campanella nella taskbar (vedi 2.2.3) verrà aggiornata con un contatore.
* Impatto sulle Performance: Il processo sarà leggero e a bassa priorità per non impattare le prestazioni dell'applicazione. Verrà eseguito solo se l'applicazione è connessa a Internet.

5. Ambito del Progetto (Scope)
5.1. Funzionalità Escluse (Out of Scope): Creazione di nuove Jira, modifica dello stato di una Jira (workflow), gestione dashboard, amministrazione di progetto.
6. Specifiche Tecniche per l'Implementazione
6.1. Stack Tecnologico: Python 3.10+, PyQt6 (o PySide6), QSS per lo stile (Fluent Design).
6.2. Architettura del Software: Pattern derivato da MVC (Model-View-Controller).
6.3. Dettagli di UI/UX e Design System:
* Palette Colori: Sfondo Principale: #2D2D30, Sfondo Secondario: #3F3F41, Colore Primario: #007ACC, Testo Principale: #F1F1F1. Colore Errore: #E74C3C, Colore Successo: #2ECC71.
* Tipografia: Font Segoe UI. Titoli: 24pt Bold, Cronometro: 48pt Bold, Corpo: 14pt.
* Iconografia: Material Design Icons.
6.4. Librerie e Dipendenze Esterne: jira, sqlite3 (standard), keyring, markdown.
6.5. Modelli di Dati (Data Models) e Schema DB
* Schema Database Locale (SQLite):
```sql
CREATE TABLE IF NOT EXISTS AppSettings (Key TEXT PRIMARY KEY NOT NULL, Value TEXT);
code
Code
CREATE TABLE IF NOT EXISTS FavoriteJiras (JiraKey TEXT PRIMARY KEY NOT NULL);

CREATE TABLE IF NOT EXISTS Annotations (Id INTEGER PRIMARY KEY AUTOINCREMENT, JiraKey TEXT NOT NULL, Title TEXT NOT NULL, Content TEXT, CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP, UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE IF NOT EXISTS SyncQueue (Id INTEGER PRIMARY KEY AUTOINCREMENT, OperationType TEXT NOT NULL, Payload TEXT NOT NULL, Status TEXT NOT NULL DEFAULT 'Pending', Attempts INTEGER NOT NULL DEFAULT 0, ErrorMessage TEXT, CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE IF NOT EXISTS LocalTimeLog (JiraKey TEXT PRIMARY KEY NOT NULL, SecondsTracked INTEGER NOT NULL DEFAULT 0, StartTime DATETIME DEFAULT CURRENT_TIMESTAMP);

-- Cronologia dei worklog registrati localmente
CREATE TABLE IF NOT EXISTS LocalWorklogHistory (Id INTEGER PRIMARY KEY AUTOINCREMENT, JiraKey TEXT NOT NULL, StartTime DATETIME NOT NULL, DurationSeconds INTEGER NOT NULL, Comment TEXT, SyncStatus TEXT NOT NULL DEFAULT 'Pending', CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP);

-- Cronologia delle issue visualizzate in dettaglio
CREATE TABLE IF NOT EXISTS ViewHistory (JiraKey TEXT PRIMARY KEY NOT NULL, LastViewedAt DATETIME NOT NULL);

-- Mappatura dei colori per gli stati
CREATE TABLE IF NOT EXISTS StatusColorMappings (StatusName TEXT PRIMARY KEY NOT NULL, ColorHex TEXT NOT NULL);

-- Cronologia delle JQL eseguite
CREATE TABLE IF NOT EXISTS JQLHistory (Id INTEGER PRIMARY KEY AUTOINCREMENT, Query TEXT NOT NULL, LastUsedAt DATETIME NOT NULL);

-- JQL salvate come preferite
CREATE TABLE IF NOT EXISTS FavoriteJQLs (Id INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT NOT NULL, Query TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS NotificationSubscriptions (JiraKey TEXT PRIMARY KEY NOT NULL, LastCheckedTimestamp DATETIME NOT NULL, LastKnownCommentId TEXT);
```
6.6. Struttura del Progetto e dei File:
* / (root): main.py, requirements.txt
* /ui: File .ui di Qt Designer.
* /views: Classi Python per la UI.
* /controllers: Logica di gestione eventi.
* /models: Classi di rappresentazione dei dati.
* /services: Logica di business (Jira, DB, Sync).
* /assets: Risorse statiche (icone, stili).

---

Implementazioni aggiuntive nel codice
-------------------------------------
Durante una verifica del codice sorgente attuale sono state individuate le seguenti funzionalità e modifiche già presenti nel codice ma non documentate nel file dei requisiti originale. Le elenco qui per tenere i requisiti e il codice sincronizzati:

- Always-on-top globale dell'applicazione
	- Campo di configurazione `always_on_top` nella schermata Impostazioni e persistenza tramite `AppSettings`.
	- Applicazione del flag Qt `WindowStaysOnTopHint` al main window e alle finestre di dettaglio (metodo `_apply_always_on_top` in `controllers/main_controller.py`).

- Migliorie alla tabella `NotificationSubscriptions`
	- Sono presenti nel database colonne aggiuntive gestite dal codice: `last_comment_date` e `is_read` (con valori di default); esistono operazioni per marcare come lette e conteggiare notifiche non lette nel DB.

- Colonna `Task` aggiunta a `LocalWorklogHistory`
	- La tabella `LocalWorklogHistory` nel codice viene aggiornata/alterata per includere una colonna `Task` con default e l'inserimento/lettura è aggiornato di conseguenza.

- Widget/mini-finestra sempre-in-primo-piano
	- La mini-widget che appare quando la finestra principale viene minimizzata imposta esplicitamente `WindowStaysOnTopHint` (vedi `views/mini_widget_view.py` e relativo controller).

- Supporto UI per PAT
	- L'input del PAT è presente nella schermata di configurazione con echo-mode impostato a password; inoltre il codice si appoggia a `services/credential_service.py` per la lettura/scrittura.

- Tabelle e migrazioni DB implementate
	- `services/db_service.py` contiene logica per creare e migrare le tabelle principali (SyncQueue, LocalWorklogHistory, NotificationSubscriptions, ecc.) e gestire operazioni di inserimento/aggiornamento/lettura.

Note e raccomandazioni
---------------------
- Raccomando di aggiornare la sezione 4.3 (Sicurezza) per specificare come il PAT è memorizzato (attualmente esiste `CredentialService` ma è opportuno specificare uso di `keyring` o equivalente e una procedura di migrazione per installazioni precedenti).
- Se desideri, posso:
	- Applicare direttamente queste modifiche nel file dei requisiti (es. aggiornare la sezione 4.3 e aggiungere i dettagli delle colonne DB aggiuntive). Questa patch le ha già elencate; posso riformattare o aggiungere link a file sorgente.

Configurazioni applicative aggiuntive (chiavi AppSettings)
-----------------------------------------------------------
Durante l'implementazione sono state aggiunte alcune chiavi di configurazione salvate in `AppSettings` (tabella `AppSettings` nel DB). Qui sotto le chiavi principali e il loro significato:

- `jira/max_retries` (int, default: 3)
	- Numero massimo di tentativi per le chiamate network verso Jira (include il primo tentativo).
- `jira/base_retry_delay` (float, default: 0.5)
	- Ritardo base (in secondi) usato per il backoff esponenziale.
- `jira/max_delay` (float, default: 30.0)
	- Limite massimo del backoff in secondi.
- `jira/non_retryable_statuses` (string, optional)
	- Lista separata da virgole di codici HTTP che non devono essere ritentati (es. `400,401,403`).
- `log_level` (string, optional)
	- Livello di logging globale (es. `DEBUG`, `INFO`, `WARNING`, `ERROR`). Se non impostata, si usano i flag `log_debug`, `log_info`, `log_warning` per filtrare la console.
- `log_max_bytes` (int, optional)
	- Dimensione massima del file di log prima della rotazione (default 5MB).
- `log_backup_count` (int, optional)
	- Numero di file di log di backup da mantenere (default 5).

Queste impostazioni sono lette all'avvio (in `main.py`) e passate a `JiraService` o al sistema di logging. Modificandole dalla UI (quando implementata) o direttamente nella tabella `AppSettings` si ottengono comportamenti differenti senza ricompilare l'applicazione.

File aggiunti per lo sviluppo
----------------------------
- `requirements-dev.txt`: elenca le dipendenze per lo sviluppo/test (es. `pytest`).

Note finali
-----------
Queste integrazioni migliorano la resilienza delle chiamate a Jira (retry con backoff, rispetto di `Retry-After`, distinzione di errori non-ripetibili), la tracciabilità tramite logging rotante e la testabilità (sleep iniettabile per i test). Se desideri, posso consolidare ulteriormente la documentazione in un README o preparare un changelog/PR.