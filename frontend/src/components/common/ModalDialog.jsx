import { useEffect, useRef } from 'react';

/**
 * Accessible modal wrapper built on native <dialog> (top-layer, Esc dismissal, focus return)
 * with closedby="any" and the pointerdown/pointerup bounds fallback for Safari.
 */
export default function ModalDialog({
  open,
  onClose,
  ariaLabel,
  ariaLabelledBy,
  maxWidthClass = 'max-w-3xl',
  panelClassName = '',
  children,
}) {
  const dialogRef = useRef(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return undefined;

    const handleClose = () => {
      dialog.returnValue = '';
      if (open && onClose) onClose();
    };

    dialog.addEventListener('close', handleClose);

    if ('closedBy' in HTMLDialogElement.prototype) {
      return () => dialog.removeEventListener('close', handleClose);
    }

    const isOutside = (e) => {
      const r = dialog.getBoundingClientRect();
      return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
    };

    let pressedOutside = false;
    const handlePointerDown = (e) => {
      pressedOutside = isOutside(e);
    };
    const handlePointerUp = (e) => {
      if (pressedOutside && isOutside(e) && dialog.open) {
        dialog.close();
      }
      pressedOutside = false;
    };

    dialog.addEventListener('pointerdown', handlePointerDown);
    dialog.addEventListener('pointerup', handlePointerUp);
    return () => {
      dialog.removeEventListener('close', handleClose);
      dialog.removeEventListener('pointerdown', handlePointerDown);
      dialog.removeEventListener('pointerup', handlePointerUp);
    };
  }, [open, onClose]);

  return (
    <dialog
      ref={dialogRef}
      closedby="any"
      aria-labelledby={ariaLabelledBy}
      aria-label={ariaLabelledBy ? undefined : ariaLabel}
      className={`modal-dialog w-full ${maxWidthClass}`}
    >
      <div
        className={`w-full max-h-[90dvh] overflow-y-auto rounded-md bg-background-primary border border-border shadow-md ${panelClassName}`}
      >
        {open ? children : null}
      </div>
    </dialog>
  );
}
