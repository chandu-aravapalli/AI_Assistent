export type Message = {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    timestamp: number;
};

export type Conversation = {
    id: string;
    title: string;
    messages: Message[];
    createdAt: number;
    updatedAt: number;
};

export type ChatResponse = {
    answer: string;
}; 