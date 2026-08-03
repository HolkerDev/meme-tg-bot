class Message < ApplicationRecord
  self.table_name = "messages"
  self.primary_key = [ :chat_id, :message_id ]

  WEEKLY_WINDOW = 7.days

  def self.distinct_chat_ids
    distinct.order(:chat_id).pluck(:chat_id)
  end

  def self.chat_summaries(since: WEEKLY_WINDOW.ago)
    group(:chat_id)
      .order(:chat_id)
      .pluck(
        :chat_id,
        Arel.sql("COUNT(*)"),
        Arel.sql(
          sanitize_sql_array(
            [ "COALESCE(SUM(CASE WHEN posted_at >= ? THEN reaction_count ELSE 0 END), 0)", since ]
          )
        )
      )
      .map do |chat_id, message_count, weekly_reaction_total|
        {
          chat_id: chat_id,
          message_count: message_count.to_i,
          weekly_reaction_total: weekly_reaction_total.to_i
        }
      end
  end

  def self.weekly_reaction_counts(chat_id, since: WEEKLY_WINDOW.ago)
    where(chat_id: chat_id)
      .where(posted_at: since..)
      .group(:user_id)
      .order(Arel.sql("SUM(reaction_count) DESC"), :user_id)
      .pluck(
        :user_id,
        Arel.sql("SUM(reaction_count)"),
        Arel.sql("MAX(username)"),
        Arel.sql("MAX(display_name)")
      )
      .map do |user_id, reaction_count, username, display_name|
        {
          user_id: user_id,
          reaction_count: reaction_count.to_i,
          username: username,
          display_name: display_name,
          label: display_label(user_id, username, display_name)
        }
      end
  end

  def self.display_label(user_id, username, display_name)
    return "@#{username}" if username.present?
    return display_name if display_name.present?

    user_id.to_s
  end
  private_class_method :display_label
end
