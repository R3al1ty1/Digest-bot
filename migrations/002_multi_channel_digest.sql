CREATE TABLE IF NOT EXISTS user_channels (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    channel VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_channels_user_channel UNIQUE (user_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_user_channels_user_id
    ON user_channels(user_id);

CREATE INDEX IF NOT EXISTS idx_user_channels_user_active
    ON user_channels(user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_user_channels_channel
    ON user_channels(channel);

CREATE TABLE IF NOT EXISTS digest_interests (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    interest VARCHAR(100) NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_digest_interests_user_interest UNIQUE (user_id, interest)
);

CREATE INDEX IF NOT EXISTS idx_digest_interests_user_id
    ON digest_interests(user_id);

ALTER TABLE digest_logs
    ADD COLUMN IF NOT EXISTS channels_count INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS channels JSONB,
    ADD COLUMN IF NOT EXISTS interests JSONB;

CREATE INDEX IF NOT EXISTS idx_digest_logs_user_created
    ON digest_logs(user_id, created_at DESC);

INSERT INTO user_channels (user_id, channel, is_active, position)
SELECT telegram_id, target_channel, TRUE, 0
FROM users
WHERE target_channel IS NOT NULL
ON CONFLICT (user_id, channel) DO NOTHING;

DROP TRIGGER IF EXISTS update_user_channels_updated_at ON user_channels;
CREATE TRIGGER update_user_channels_updated_at
    BEFORE UPDATE ON user_channels
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_digest_interests_updated_at ON digest_interests;
CREATE TRIGGER update_digest_interests_updated_at
    BEFORE UPDATE ON digest_interests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
