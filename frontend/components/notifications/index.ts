/**
 * Sistema de notificaciones: toasts (éxito, error, info) y diálogos de confirmación.
 * Sustituye alert() y confirm() del navegador por una UX consistente con el diseño de la app.
 */
export { toast } from '@/components/ui/sonner';
export { useConfirmDialog, NotificationProvider } from '@/contexts/NotificationContext';
export type { ConfirmOptions, ConfirmVariant } from '@/contexts/NotificationContext';
