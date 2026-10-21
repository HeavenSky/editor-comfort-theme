require 'json'

module Jobs
  class Sync < Base
    RETRIES = 3
    attr_reader :name

    def initialize(name, opts = {})
      @name = name
      @verbose = opts.fetch(:verbose, false)
    end

    def call
      items = fetch_items.select { |i| i[:active] && i[:score] > 0.5 }
      puts "synced #{items.size} items" if @verbose
      items.map(&:to_json)
    end
  end
end
