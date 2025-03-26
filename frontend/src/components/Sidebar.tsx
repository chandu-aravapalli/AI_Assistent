import { Conversation } from '@/types/chat';

interface SidebarProps {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  onNewChat: () => void;
  onSelectConversation: (conversation: Conversation) => void;
  onDeleteConversation: (conversationId: string) => void;
}

export default function Sidebar({
  conversations,
  currentConversation,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
}: SidebarProps) {
  return (
    <div className="w-[260px] bg-[#1E1F23] h-screen flex flex-col">
      {/* New Chat Button */}
      <div className="p-2">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2 text-sm text-white/80 hover:bg-white/10 rounded-lg py-3 px-3 transition-colors border border-white/20"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M12 4L12 20M20 12L4 12"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
          New chat
        </button>
      </div>

      {/* Today Section */}
      <div className="px-2 py-2">
        <h3 className="text-xs text-white/50 font-medium px-3 py-2">Today</h3>
        <div className="space-y-1">
          {conversations.map((conversation) => {
            const isToday =
              new Date(conversation.createdAt).toDateString() ===
              new Date().toDateString();
            if (!isToday) return null;

            return (
              <div
                key={conversation.id}
                className={`group flex items-center gap-2 rounded-lg py-3 px-3 text-sm cursor-pointer ${
                  currentConversation?.id === conversation.id
                    ? 'bg-[#2D2E35] text-white'
                    : 'text-white/80 hover:bg-[#2A2B32]'
                }`}
                onClick={() => onSelectConversation(conversation)}
              >
                <svg
                  className="w-4 h-4 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                  />
                </svg>
                <span className="truncate flex-1">
                  {conversation.title || 'New Chat'}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conversation.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 hover:text-red-400"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
