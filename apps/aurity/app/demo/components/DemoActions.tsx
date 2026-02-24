import { Database, RefreshCw, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

import type { ConfirmAction } from '../types';

interface DemoActionsProps {
  isLoaded: boolean;
  isLoading: boolean;
  showConfirm: ConfirmAction;
  onShowConfirm: (action: ConfirmAction) => void;
  onLoadDemo: () => Promise<void>;
  onResetDemo: () => Promise<void>;
}

export function DemoActions({
  isLoaded,
  isLoading,
  showConfirm,
  onShowConfirm,
  onLoadDemo,
  onResetDemo,
}: DemoActionsProps) {
  return (
    <>
      {/* Action Buttons */}
      <div className="demo-actions">
        {!isLoaded ? (
          <Button
            onClick={() => onShowConfirm('load')}
            disabled={isLoading}
            loading={isLoading}
            variant="purple"
            size="lg"
            icon={Database}
          >
            Load Demo Dataset
          </Button>
        ) : (
          <>
            <Button
              onClick={() => onShowConfirm('load')}
              disabled={isLoading}
              loading={isLoading}
              variant="purple"
              size="lg"
              icon={RefreshCw}
            >
              Reload Dataset
            </Button>
            <Button
              onClick={() => onShowConfirm('reset')}
              disabled={isLoading}
              variant="secondary"
              size="lg"
              icon={Trash2}
            >
              Reset Demo
            </Button>
          </>
        )}
      </div>

      {/* Confirmation Dialog */}
      {showConfirm && (
        <div className="demo-confirm">
          <p className="demo-confirm-text">
            {showConfirm === 'load'
              ? 'This will load 3 demo sessions with sample events. Continue?'
              : 'This will remove all demo data. Continue?'}
          </p>
          <div className="demo-confirm-actions">
            <Button
              onClick={showConfirm === 'load' ? onLoadDemo : onResetDemo}
              disabled={isLoading}
              loading={isLoading}
              variant={showConfirm === 'load' ? 'purple' : 'danger'}
            >
              Confirm
            </Button>
            <Button
              onClick={() => onShowConfirm(null)}
              disabled={isLoading}
              variant="secondary"
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
