import os
import subprocess

def _print_via_escpos(text: str):
    """Print via USB escpos library (direct USB connection)."""
    from escpos.printer import Usb
    vendor = int(os.getenv("ESCPOS_USB_VENDOR_ID", "0"), 16)
    product = int(os.getenv("ESCPOS_USB_PRODUCT_ID", "0"), 16)
    in_ep = int(os.getenv("ESCPOS_IN_EP", "0"), 16) if os.getenv("ESCPOS_IN_EP") else None
    out_ep = int(os.getenv("ESCPOS_OUT_EP", "0"), 16) if os.getenv("ESCPOS_OUT_EP") else None

    p = Usb(vendor, product, in_ep=in_ep, out_ep=out_ep, timeout=0)
    try:
        p.set(align="center", width=1, height=1)
        for line in text.split("\n"):
            p.text(line + "\n")
        p.cut()
    finally:
        # Release the USB interface, or the next ticket gets "Access denied".
        p.close()

def _print_via_os(text: str):
    """Print via system lpr/CUPS (works with PRINTER env var)."""
    printer = os.getenv("PRINTER", "") or os.getenv("PRINTER_NAME", "")
    cmd = ["lpr"]
    if printer:
        cmd += ["-P", printer]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate(input=text.encode("utf-8"))

    if proc.returncode != 0:
        raise RuntimeError(f"lpr failed (exit {proc.returncode}): {stderr.decode('utf-8', errors='ignore')}")

def print_ticket(text: str):
    """
    Print ticket with fallback strategy:
    1. Try USB escpos if ESCPOS_USB_VENDOR_ID is set
    2. Fall back to system lpr (respects PRINTER or PRINTER_NAME env vars)
    3. Raise exception if both fail
    """
    errors = []

    # Try USB escpos first if configured
    if os.getenv("ESCPOS_USB_VENDOR_ID"):
        try:
            _print_via_escpos(text)
            return  # Success
        except Exception as e:
            errors.append(f"USB escpos failed: {e}")
            # Fall through to try lpr

    # Try system lpr (primary method if no USB, fallback otherwise)
    try:
        _print_via_os(text)
        return  # Success
    except Exception as e:
        errors.append(f"System lpr failed: {e}")

    # Both methods failed
    raise RuntimeError(f"All print methods failed:\n" + "\n".join(errors))
