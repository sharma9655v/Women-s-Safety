"use client";

import { Heart, MessageCircle, ShieldCheck } from "lucide-react";
import { Avatar } from "@/app/components/ui/Avatar";
import { Badge } from "@/app/components/ui/Badge";
import { Card, CardHeader } from "@/app/components/ui/Card";
import type { CommunityPost } from "@/lib/types";

function PostCard({ post }: { post: CommunityPost }) {
  return (
    <div className="flex gap-3 rounded-xl border border-border bg-surface p-3 transition-colors duration-200 hover:border-border-glow hover:bg-surface-hover">
      <Avatar
        initials={post.author_initials}
        label={post.author}
        index={parseInt(post.id, 10) || 0}
        size="sm"
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-foreground">{post.author}</span>
          {post.verified ? (
            <ShieldCheck className="size-3 text-info" aria-label="Verified" />
          ) : null}
          <Badge
            tone={
              post.kind === "alert" ? "danger" : post.kind === "route_update" ? "success" : "info"
            }
          >
            {post.kind.replace(/_/g, " ")}
          </Badge>
        </div>
        <p className="mt-1 text-xs text-text-secondary leading-relaxed">{post.text}</p>
        <div className="mt-1.5 flex items-center gap-3 text-[10px] text-text-muted">
          <span>{post.location}</span>
          <span>{post.time_ago}</span>
          <span className="flex items-center gap-0.5">
            <Heart className="size-3" aria-hidden /> {post.likes}
          </span>
          <span className="flex items-center gap-0.5">
            <MessageCircle className="size-3" aria-hidden /> {post.comments}
          </span>
        </div>
      </div>
    </div>
  );
}

export function CommunityFeed({ posts }: { posts: CommunityPost[] }) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader title="Community Feed" subtitle="Anonymous updates from verified members" />
      {posts.length === 0 ? (
        <p className="py-6 text-center text-xs text-text-muted">No community posts yet.</p>
      ) : (
        <div className="flex-1 space-y-2 overflow-y-auto">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </Card>
  );
}
