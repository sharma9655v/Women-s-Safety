"use client";

import { CheckCircle, Headphones, MapPin, Phone } from "lucide-react";

const ACTIONS = [
  {
    id: "fake-call",
    label: "Fake Call",
    icon: Phone,
    description: "Simulate incoming call",
  },
  {
    id: "voice-guide",
    label: "Voice Guide",
    icon: Headphones,
    description: "Audio navigation",
  },
  {
    id: "nearby-help",
    label: "Nearby Help",
    icon: MapPin,
    description: "Find safe places",
  },
  {
    id: "check-in",
    label: "Check-in",
    icon: CheckCircle,
    description: "Share status update",
  },
];

export function QuickActionsGrid({
  onAction,
}: {
  onAction: (actionId: string) => void;
}) {
  return (
    <div className="quick-actions-grid">
      {ACTIONS.map((action) => {
        const Icon = action.icon;
        return (
          <button
            key={action.id}
            type="button"
            className="quick-action-btn"
            onClick={() => onAction(action.id)}
            title={action.description}
          >
            <span className="quick-action-icon">
              <Icon className="size-4.5" aria-hidden />
            </span>
            <span>{action.label}</span>
          </button>
        );
      })}
    </div>
  );
}
