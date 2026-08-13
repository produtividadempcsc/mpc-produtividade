import platform
import threading

# Tentar importar docx2pdf (só funciona no Windows)
try:
    from docx2pdf import convert
    DOCX2PDF_AVAILABLE = True
except ImportError:
    DOCX2PDF_AVAILABLE = False
    convert = None

# Tenta importar o pythoncom, necessário para conversão de .docx no Windows
try:
    if platform.system() == "Windows":
        import pythoncom
    else:
        pythoncom = None
except ImportError:
    print("AVISO: Módulo 'pywin32' não instalado. A conversão de .docx pode não funcionar no Windows.")
    pythoncom = None

def convert_docx_to_pdf_threaded(docx_path, pdf_path):
    """
    Converts a .docx file to .pdf in a separate thread to handle COM initialization correctly.
    """
    # Verificar se docx2pdf está disponível
    if not DOCX2PDF_AVAILABLE:
        raise NotImplementedError(
            "Conversão de DOCX para PDF não está disponível neste ambiente. "
            "Esta funcionalidade só está disponível no Windows."
        )
    
    if not pythoncom:
        # Fallback for non-Windows systems or missing pythoncom
        convert(docx_path, pdf_path)
        return

    result = {}

    def conversion_thread():
        pythoncom.CoInitialize()
        try:
            convert(docx_path, pdf_path)
            result['success'] = True
        except Exception as e:
            result['success'] = False
            result['error'] = e
        finally:
            pythoncom.CoUninitialize()

    thread = threading.Thread(target=conversion_thread)
    thread.start()
    thread.join()

    if not result.get('success', False):
        raise result.get('error', Exception("Unknown error during conversion."))
