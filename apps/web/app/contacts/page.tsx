"use client";

import { Loader2, Phone, Plus, Trash2, UserRound } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { Badge } from "@/app/components/ui/Badge";
import { Button } from "@/app/components/ui/Button";
import { Card } from "@/app/components/ui/Card";
import { Input, Select } from "@/app/components/ui/Input";
import { createContact, deleteContact, fetchContacts, updateContact } from "@/lib/api";
import type { ContactRole, TrustedContact } from "@/lib/types";

const EMPTY_FORM = { name: "", relationship: "", phone: "", role: "primary" as ContactRole };

export default function ContactsPage() {
  const [contacts, setContacts] = useState<TrustedContact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [removing, setRemoving] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchContacts()
      .then((c) => {
        if (!cancelled) setContacts(c);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load your trusted contacts.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.phone.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await createContact({
        name: form.name.trim(),
        relationship: form.relationship.trim() || "friend",
        phone: form.phone.trim(),
        role: form.role,
      });
      setContacts((prev) => [...prev, created]);
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add the contact.");
    } finally {
      setSaving(false);
    }
  };

  const toggle = async (c: TrustedContact) => {
    try {
      const updated = await updateContact(c.id, { enabled: !c.enabled });
      setContacts((prev) => prev.map((x) => (x.id === c.id ? updated : x)));
    } catch {
      setError("Could not update the contact.");
    }
  };

  const remove = async (c: TrustedContact) => {
    setRemoving(c.id);
    setError(null);
    try {
      await deleteContact(c.id);
      setContacts((prev) => prev.filter((x) => x.id !== c.id));
    } catch {
      setError("Could not remove the contact.");
    } finally {
      setRemoving(null);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-4 p-4 lg:p-6">
        <header>
          <h1 className="text-xl font-bold text-foreground">
            <span className="text-primary">Trusted Contacts</span>
          </h1>
          <p className="text-sm text-text-muted">
            People you can reach in an emergency. Phone numbers are encrypted at rest and only shown
            to you.
          </p>
        </header>

        {error ? (
          <p className="glass rounded-2xl p-4 text-center text-sm text-danger">{error}</p>
        ) : null}

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-foreground">Add a contact</h2>
          <form onSubmit={submit} className="space-y-3">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Input
                id="contact-name"
                label="Name"
                placeholder="e.g. Mother"
                value={form.name}
                maxLength={60}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                required
              />
              <Input
                id="contact-relationship"
                label="Relationship"
                placeholder="e.g. family, friend"
                value={form.relationship}
                maxLength={30}
                onChange={(e) => setForm((f) => ({ ...f, relationship: e.target.value }))}
              />
              <Input
                id="contact-phone"
                label="Phone"
                type="tel"
                placeholder="+91…"
                value={form.phone}
                minLength={7}
                maxLength={20}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                required
              />
              <Select
                id="contact-role"
                label="Role"
                value={form.role}
                onChange={(e) => setForm((f) => ({ ...f, role: e.target.value as ContactRole }))}
              >
                <option value="primary">Primary</option>
                <option value="secondary">Secondary</option>
              </Select>
            </div>
            <Button type="submit" loading={saving} size="sm">
              <Plus className="size-3.5" aria-hidden /> Add contact
            </Button>
          </form>
        </Card>

        {loading ? (
          <div className="space-y-3">
            <Card>
              <div className="flex items-center gap-2 text-sm text-text-muted">
                <Loader2 className="size-4 animate-spin" aria-hidden /> Loading contacts…
              </div>
            </Card>
          </div>
        ) : contacts.length === 0 ? (
          <p className="glass rounded-2xl p-4 text-center text-sm text-text-muted">
            No trusted contacts yet. Add at least one so SOS can share your location with them.
          </p>
        ) : (
          <div className="space-y-2.5">
            {contacts.map((c) => (
              <Card key={c.id} className="flex items-center gap-3 p-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <UserRound className="size-4" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 text-sm font-semibold text-foreground">
                    {c.name}
                    <Badge tone={c.role === "primary" ? "primary" : "default"}>{c.role}</Badge>
                  </p>
                  <p className="flex items-center gap-1.5 text-xs text-text-muted">
                    <Phone className="size-3" aria-hidden />
                    {c.phone} · {c.relationship}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void toggle(c)}
                  className={`cursor-pointer rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors ${
                    c.enabled
                      ? "border-success/30 bg-success/10 text-success"
                      : "border-border bg-surface text-text-muted"
                  }`}
                  aria-label={`${c.enabled ? "Disable" : "Enable"} ${c.name}`}
                >
                  {c.enabled ? "Enabled" : "Disabled"}
                </button>
                <Button
                  variant="ghost"
                  size="sm"
                  loading={removing === c.id}
                  onClick={() => void remove(c)}
                  aria-label={`Remove ${c.name}`}
                >
                  <Trash2 className="size-3.5 text-danger" aria-hidden />
                </Button>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
