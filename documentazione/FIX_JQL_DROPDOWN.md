# Fix JQL Dropdown Bug

## 🐛 Problema Identificato

La dropdown JQL non funzionava quando l'utente digitava manualmente una query JQL.

### Causa Principale

Il metodo `get_jql_text()` nella classe `JiraGridView` aveva un bug nella logica:

```python
# CODICE BUGGATO
def get_jql_text(self):
    current_index = self.jql_combo.currentIndex()
    if current_index >= 0:  # ❌ PROBLEMA QUI
        # ... gestione item selezionati
    return ""  # ❌ Ritornava sempre stringa vuota per testo manuale
```

**Il problema**: Quando l'utente digita manualmente una query JQL usando `setCurrentText()`, il `currentIndex()` diventa `-1` perché il testo non corrisponde a nessun item nella lista. Il metodo controllava solo `current_index >= 0`, ignorando completamente il testo manuale.

## ✅ Soluzione Implementata

```python
# CODICE CORRETTO
def get_jql_text(self):
    current_index = self.jql_combo.currentIndex()
    current_text = self.jql_combo.currentText()
    
    # ✅ GESTISCI TESTO MANUALE (index -1)
    if current_index < 0:
        return current_text
        
    # ✅ GESTISCI ITEM SELEZIONATI (index >= 0)
    if current_index >= 0:
        item_data = self.jql_combo.itemData(current_index)
        if item_data is not None:
            return item_data  # Preferito selezionato
        else:
            if current_text == "📚 Gestisci cronologia e preferiti...":
                return ""  # Opzione di gestione
            else:
                return current_text  # Testo normale
    return ""
```

## 🧪 Test di Verifica

I test hanno confermato che ora la dropdown funziona correttamente:

- ✅ **Testo manuale**: `assignee = currentUser()` → ritorna `assignee = currentUser()`
- ✅ **Preferiti**: Selezionando un preferito → ritorna la query completa
- ✅ **Opzione gestione**: Selezionando "📚 Gestisci..." → ritorna stringa vuota
- ✅ **Casi edge**: Stringa vuota, query complesse → gestiti correttamente

## 📋 Comportamento Finale

1. **Digitazione manuale**: L'utente può digitare liberamente query JQL
2. **Selezione preferiti**: Funziona come prima, con query complete
3. **Compatibilità**: Nessuna breaking change per codice esistente
4. **Edge cases**: Tutti i casi limite sono gestiti correttamente

## 🔄 Impact

- **Controllers che usano `get_jql_text()`**: Ora ricevono il testo corretto
- **Ricerca JIRA**: Funziona con query manuali e preferiti
- **UX**: Dropdown completamente funzionale per l'utente finale

La fix è **backwards compatible** e risolve completamente il problema segnalato.

---

*Fix implementata il: $(Get-Date)*
*File modificato: `views/jira_grid_view.py`*
*Metodo: `get_jql_text()`*