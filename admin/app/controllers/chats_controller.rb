class ChatsController < ApplicationController
  def index
    @chats = Message.chat_summaries
  end

  def show
    @chat_id = params[:id].to_i
    @since = Message::WEEKLY_WINDOW.ago
    @entries = Message.weekly_reaction_counts(@chat_id, since: @since)
  end
end
