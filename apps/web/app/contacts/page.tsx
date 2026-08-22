"use client";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { UserPlus, UserCheck, UserX, Phone, Mail, Star, UserMinus, Loader2, Edit, Trash2 } from "lucide-react";
import { formatDistance } from "@/lib/format";

export default function ContactsPage() {
  const { data, mutate } = useQuery("contacts-page", () => api.contacts.list(), { revalidateMs: 30_000 });
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<import("@/lib/types").TrustedContact | null>(null);
  const [form, setForm] = useState({ name: "", relationship: "", phone: "", role: "primary" as "primary" | "secondary", enabled: true });

  const openCreate = () => { setEditing(null); setForm({ name: "", relationship: "", phone: "", role: "primary", enabled: true }); setShowModal(true); };
  const openEdit = (c: import("@/lib/types").TrustedContact) => { setEditing(c); setForm({ name: c.name, relationship: c.relationship, phone: c.phone, role: c.role, enabled: c.enabled }); setShowModal(true); };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editing) await api.contacts.update(editing.id, form);
      else await api.contacts.create(form);
      setShowModal(false);
      mutate();
    } catch { alert("Failed"); }
  };

  const remove = async (id: number) => { if (confirm("Remove this contact?")) { await api.contacts.remove(id); mutate(); } };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="p-4 sm:p-6 border-b border-line">
        <div className="mx-auto max-w-xl flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-bold">Trusted Contacts</h1>
            <p className="text-sm text-text-mid">Contacts notified during emergencies, guardian journeys, and location sharing.</p>
          </div>
          <Button onClick={openCreate}><UserPlus size={16} /> Add Contact</Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-xl space-y-3">
          {data?.contacts?.length === 0 ? (
            <Card variant="glass" className="text-center py-12"><UserPlus size={48} className="mx-auto text-text-low mb-4" /><p className="text-text-mid">No contacts yet</p><Button className="mt-4" onClick={openCreate}>Add First Contact</Button></Card>
          ) : (
            data?.contacts?.map(c => (
              <Card key={c.id} variant="glass" className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="size-12 rounded-xl bg-primary/20 flex items-center justify-center"><UserCheck size={20} className="text-primary" /></div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{c.name}</span>
                      <Badge variant={c.role === "primary" ? "success" : "info"}> {c.role} </Badge>
                      <Badge variant={c.enabled ? "success" : "default"}> {c.enabled ? "Active" : "Inactive"} </Badge>
                    </div>
                    <p className="text-sm text-text-mid flex items-center gap-1"><Phone size={14} /> {c.phone} • {c.relationship}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" onClick={() => openEdit(c)}><Edit size={16} /></Button>
                  <Button variant="ghost" size="icon" danger onClick={() => remove(c.id)}><Trash2 size={16} /></Button>
                </div>
              </Card>
            ))
          )}
        </div>
      </div>

      <Modal open={showModal} onClose={() => setShowModal(false)} title={editing ? "Edit Contact" : "Add Contact"}>
        <form onSubmit={submit} className="space-y-4">
          <Input label="Name" placeholder="e.g., Priya Sharma" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
          <Input label="Relationship" placeholder="e.g., Sister, Friend, Parent" value={form.relationship} onChange={e => setForm(f => ({ ...f, relationship: e.target.value }))} required />
          <Input label="Phone" type="tel" placeholder="+91 9XXXXXXXXX" value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} required />
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="flex items-center gap-2 cursor-pointer"><input type="radio" name="role" value="primary" checked={form.role === "primary"} onChange={() => setForm(f => ({ ...f, role: "primary" }))} className="accent-primary" /><Star size={16} className="text-warn" /><span>Primary</span></label>
            <label className="flex items-center gap-2 cursor-pointer"><input type="radio" name="role" value="secondary" checked={form.role === "secondary"} onChange={() => setForm(f => ({ ...f, role: "secondary" }))} className="accent-primary" /><UserCheck size={16} /><span>Secondary</span></label>
          </div>
          <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={form.enabled} onChange={e => setForm(f => ({ ...f, enabled: e.target.checked }))} className="accent-primary" /><span>Enabled for notifications</span></label>
          <div className="flex gap-2 pt-2">
            <Button type="submit" className="flex-1">{editing ? "Save" : "Add"} Contact</Button>
            <Button type="button" variant="ghost" onClick={() => setShowModal(false)}>Cancel</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}