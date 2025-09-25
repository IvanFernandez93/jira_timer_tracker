"""
External Diff Service - Integrazione con diff viewer esterni
Supporta VS Code, Beyond Compare, WinMerge, Notepad++ e altri tool di diff
"""
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, List
import logging

logger = logging.getLogger(__name__)

class ExternalDiffService:
    """Servizio per aprire diff esterni con vari tool."""
    
    def __init__(self):
        self.supported_tools = {
            "VS Code (code --diff)": self._open_vscode_diff,
            "Beyond Compare": self._open_beyond_compare,
            "WinMerge": self._open_winmerge,
            "Notepad++ Compare": self._open_notepadpp_diff,
            "Git Diff Tool": self._open_git_diff,
            "Personalizzato...": self._open_custom_diff
        }
        
        # Directory temporanea per i file diff
        self.temp_dir = None
        
    def __enter__(self):
        """Context manager per gestire file temporanei."""
        self.temp_dir = tempfile.mkdtemp(prefix="jira_diff_")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup file temporanei."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.warning(f"Errore cleanup temp dir: {e}")
                
    def open_diff(self, content1: str, content2: str, 
                  label1: str = "Version 1", label2: str = "Version 2",
                  tool: str = "VS Code (code --diff)") -> bool:
        """
        Apre un diff esterno tra due contenuti.
        
        Args:
            content1: Contenuto del primo file
            content2: Contenuto del secondo file  
            label1: Etichetta per il primo file
            label2: Etichetta per il secondo file
            tool: Nome del tool da usare
            
        Returns:
            True se il diff è stato aperto con successo
        """
        try:
            # Crea file temporanei
            file1_path, file2_path = self._create_temp_files(content1, content2, label1, label2)
            
            if not file1_path or not file2_path:
                return False
                
            # Usa il tool specificato
            if tool in self.supported_tools:
                return self.supported_tools[tool](file1_path, file2_path)
            else:
                logger.error(f"Tool non supportato: {tool}")
                return False
                
        except Exception as e:
            logger.error(f"Errore apertura diff esterno: {e}")
            return False
            
    def _create_temp_files(self, content1: str, content2: str, 
                          label1: str, label2: str) -> Tuple[Optional[str], Optional[str]]:
        """Crea file temporanei per il diff."""
        try:
            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp(prefix="jira_diff_")
                
            # Sanitizza i nomi file
            safe_label1 = self._sanitize_filename(label1)
            safe_label2 = self._sanitize_filename(label2)
            
            # Crea i file
            file1_path = os.path.join(self.temp_dir, f"{safe_label1}.md")
            file2_path = os.path.join(self.temp_dir, f"{safe_label2}.md")
            
            with open(file1_path, 'w', encoding='utf-8') as f:
                f.write(content1 or "")
                
            with open(file2_path, 'w', encoding='utf-8') as f:
                f.write(content2 or "")
                
            return file1_path, file2_path
            
        except Exception as e:
            logger.error(f"Errore creazione file temporanei: {e}")
            return None, None
            
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitizza un nome file per rimuovere caratteri non validi."""
        # Rimuovi caratteri non consentiti nei nomi file
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename[:100]  # Limita lunghezza
        
    def _open_vscode_diff(self, file1_path: str, file2_path: str) -> bool:
        """Apre il diff in VS Code."""
        try:
            # Prova prima "code" poi il path completo su Windows
            commands_to_try = [
                ["code", "--diff", file1_path, file2_path],
            ]
            
            # Su Windows, prova anche path comuni di VS Code
            if os.name == 'nt':
                vscode_paths = [
                    os.path.expanduser("~/AppData/Local/Programs/Microsoft VS Code/bin/code.cmd"),
                    "C:\\Program Files\\Microsoft VS Code\\bin\\code.cmd",
                    "C:\\Program Files (x86)\\Microsoft VS Code\\bin\\code.cmd"
                ]
                
                for path in vscode_paths:
                    if os.path.exists(path):
                        commands_to_try.append([path, "--diff", file1_path, file2_path])
                        
            # Prova i comandi
            for cmd in commands_to_try:
                try:
                    subprocess.Popen(cmd)
                    logger.info(f"VS Code diff aperto: {' '.join(cmd)}")
                    return True
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
                    
            logger.error("VS Code non trovato nel PATH o nelle posizioni standard")
            return False
            
        except Exception as e:
            logger.error(f"Errore apertura VS Code: {e}")
            return False
            
    def _open_beyond_compare(self, file1_path: str, file2_path: str) -> bool:
        """Apre il diff in Beyond Compare."""
        try:
            # Path comuni per Beyond Compare
            bc_paths = []
            
            if os.name == 'nt':  # Windows
                bc_paths = [
                    "BCompare.exe",
                    "C:\\Program Files\\Beyond Compare 4\\BCompare.exe",
                    "C:\\Program Files (x86)\\Beyond Compare 4\\BCompare.exe",
                    "C:\\Program Files\\Beyond Compare 5\\BCompare.exe",
                    "C:\\Program Files (x86)\\Beyond Compare 5\\BCompare.exe"
                ]
            else:  # Linux/Mac
                bc_paths = [
                    "bcompare",
                    "/usr/bin/bcompare",
                    "/Applications/Beyond Compare.app/Contents/MacOS/bcomp"
                ]
                
            for bc_path in bc_paths:
                try:
                    subprocess.Popen([bc_path, file1_path, file2_path])
                    logger.info(f"Beyond Compare aperto: {bc_path}")
                    return True
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
                    
            logger.error("Beyond Compare non trovato")
            return False
            
        except Exception as e:
            logger.error(f"Errore apertura Beyond Compare: {e}")
            return False
            
    def _open_winmerge(self, file1_path: str, file2_path: str) -> bool:
        """Apre il diff in WinMerge (solo Windows)."""
        try:
            if os.name != 'nt':
                logger.error("WinMerge disponibile solo su Windows")
                return False
                
            winmerge_paths = [
                "WinMergeU.exe",
                "C:\\Program Files\\WinMerge\\WinMergeU.exe",
                "C:\\Program Files (x86)\\WinMerge\\WinMergeU.exe"
            ]
            
            for wm_path in winmerge_paths:
                try:
                    subprocess.Popen([wm_path, file1_path, file2_path])
                    logger.info(f"WinMerge aperto: {wm_path}")
                    return True
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
                    
            logger.error("WinMerge non trovato")
            return False
            
        except Exception as e:
            logger.error(f"Errore apertura WinMerge: {e}")
            return False
            
    def _open_notepadpp_diff(self, file1_path: str, file2_path: str) -> bool:
        """Apre il diff nel plugin Compare di Notepad++."""
        try:
            if os.name != 'nt':
                logger.error("Notepad++ disponibile principalmente su Windows")
                return False
                
            npp_paths = [
                "notepad++.exe",
                "C:\\Program Files\\Notepad++\\notepad++.exe",
                "C:\\Program Files (x86)\\Notepad++\\notepad++.exe"
            ]
            
            for npp_path in npp_paths:
                try:
                    # Apre i due file in Notepad++
                    subprocess.Popen([npp_path, file1_path, file2_path])
                    logger.info(f"Notepad++ aperto: {npp_path}")
                    logger.info("Nota: usa il plugin Compare di Notepad++ per vedere le differenze")
                    return True
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
                    
            logger.error("Notepad++ non trovato")
            return False
            
        except Exception as e:
            logger.error(f"Errore apertura Notepad++: {e}")
            return False
            
    def _open_git_diff(self, file1_path: str, file2_path: str) -> bool:
        """Apre il diff usando il diff tool configurato in Git."""
        try:
            # Usa git difftool per aprire il diff esterno configurato
            result = subprocess.run([
                "git", "difftool", "--no-prompt", 
                "--extcmd=echo", file1_path, file2_path
            ], cwd=self.temp_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Git difftool aperto")
                return True
            else:
                logger.error(f"Errore git difftool: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Errore apertura git difftool: {e}")
            return False
            
    def _open_custom_diff(self, file1_path: str, file2_path: str) -> bool:
        """Apre un diff personalizzato (da configurare)."""
        try:
            # Per ora apre il file manager per mostrare i file
            if os.name == 'nt':
                os.startfile(self.temp_dir)
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', self.temp_dir])
                
            logger.info(f"File temporanei creati in: {self.temp_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Errore apertura diff personalizzato: {e}")
            return False
            
    def get_available_tools(self) -> List[str]:
        """Restituisce la lista dei tool di diff disponibili sul sistema."""
        available = []
        
        # Verifica VS Code
        try:
            subprocess.run(["code", "--version"], 
                          capture_output=True, check=True, timeout=5)
            available.append("VS Code (code --diff)")
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
            
        # Verifica Beyond Compare
        bc_paths = ["BCompare.exe", "bcompare"] if os.name == 'nt' else ["bcompare"]
        for bc_path in bc_paths:
            try:
                subprocess.run([bc_path, "/?"], 
                              capture_output=True, timeout=5)
                available.append("Beyond Compare")
                break
            except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
                
        # Verifica WinMerge (solo Windows)
        if os.name == 'nt':
            try:
                if any(os.path.exists(p) for p in [
                    "C:\\Program Files\\WinMerge\\WinMergeU.exe",
                    "C:\\Program Files (x86)\\WinMerge\\WinMergeU.exe"
                ]):
                    available.append("WinMerge")
            except Exception:
                pass
                
        # Verifica Git
        try:
            subprocess.run(["git", "--version"], 
                          capture_output=True, check=True, timeout=5)
            available.append("Git Diff Tool")
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
            
        # Personalizzato è sempre disponibile
        available.append("Personalizzato...")
        
        return available
        
    def detect_best_tool(self) -> str:
        """Rileva il miglior tool disponibile."""
        available = self.get_available_tools()
        
        # Priorità: VS Code > Beyond Compare > WinMerge > Git > Personalizzato
        priority_order = [
            "VS Code (code --diff)",
            "Beyond Compare", 
            "WinMerge",
            "Git Diff Tool",
            "Personalizzato..."
        ]
        
        for tool in priority_order:
            if tool in available:
                return tool
                
        return "Personalizzato..."
        
    @staticmethod
    def create_diff_context_manager():
        """Crea un context manager per gestire automaticamente la cleanup."""
        return ExternalDiffService()