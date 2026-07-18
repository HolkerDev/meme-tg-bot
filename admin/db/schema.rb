# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[8.1].define(version: 0) do
  create_table "alembic_version", primary_key: "version_num", id: { type: :string, limit: 32 }, force: :cascade do |t|
  end

# Could not dump table "chat_stats_state" because of following StandardError
#   Unknown type 'REAL' for column 'last_published_at'


# Could not dump table "link_posts" because of following StandardError
#   Unknown type 'REAL' for column 'posted_at'


# Could not dump table "posted_media" because of following StandardError
#   Unknown type 'REAL' for column 'posted_at'


  create_table "reactions", id: :integer, default: nil, force: :cascade do |t|
    t.integer "chat_id", null: false
    t.datetime "timestamp", precision: nil, null: false
    t.integer "user_id", null: false
  end

# Could not dump table "reactions_received" because of following StandardError
#   Unknown type 'REAL' for column 'reacted_at'


# Could not dump table "retry_queue" because of following StandardError
#   Unknown type 'REAL' for column 'created_at'


# Could not dump table "tracked_messages" because of following StandardError
#   Unknown type 'REAL' for column 'registered_at'

end
