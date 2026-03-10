# *******************************************************************************
# Honeybee OpenStudio Gem, Copyright (c) 2020, Alliance for Sustainable
# Energy, LLC, Ladybug Tools LLC and other contributors. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# (1) Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# (2) Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# (3) Neither the name of the copyright holder nor the names of any contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission from the respective party.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER(S) AND ANY CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER(S), ANY CONTRIBUTORS, THE
# UNITED STATES GOVERNMENT, OR THE UNITED STATES DEPARTMENT OF ENERGY, NOR ANY OF
# THEIR EMPLOYEES, BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
# OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# *******************************************************************************

require 'urbanopt/reporting'
require 'openstudio/common_measures'
require 'openstudio/model_articulation'

require 'json'

module URBANopt
    module Scenario
      class HoneybeeMapper < SimulationMapperBase

      # class level variables
      @@instance_lock = Mutex.new
      @@osw = nil
      @@mapper_measures = nil
      @@geometry = nil

      def initialize()
        # do initialization of class variables in thread safe way
        @@instance_lock.synchronize do
          # load the OSW for this class
          if @@osw.nil?
            osw_path = File.join(File.dirname(__FILE__), 'honeybee_workflow.osw')
            File.open(osw_path, 'r') do |file|
              @@osw = JSON.parse(file.read, symbolize_names: true)
            end
          # configure OSW with extension gem paths for measures and files
          # all extension gems must be required before this line
          @@osw = OpenStudio::Extension.configure_osw(@@osw)
          end

          # load the mapper measure variables if the file exists
          if @@mapper_measures.nil?
            map_meas_path = File.join(File.dirname(__FILE__), 'mapper_measures.json')
            if File.file?(map_meas_path)
              File.open(map_meas_path, 'r') do |file|
                @@mapper_measures = JSON.parse(file.read)
              end
            end
          end

        end
      end

      def create_osw(scenario, features, feature_names)

        if features.size != 1
          raise "Mapper currently cannot simulate more than one feature at a time."
        end
        feature = features[0]
        feature_id = feature.id
        feature_type = feature.type
        feature_name = feature.name

        # take the centroid of the vertices as the location of the building
        feature_vertices_coordinates = feature.feature_json[:geometry][:coordinates][0]
        feature_location = feature.find_feature_center(feature_vertices_coordinates).to_s
        if feature_names.size == 1
          feature_name = feature_names[0]
        end

        # deep clone of @@osw before we configure it
        osw = Marshal.load(Marshal.dump(@@osw))

        # set the name and description of the OSW to reference this particular feature
        osw[:name] = feature_name
        osw[:description] = feature_name

        if feature_type == 'Building'
            # set the honeybee JSON key to the honeybee_model measure
            OpenStudio::Extension.set_measure_argument(
                osw, 'from_honeybee_model', 'model_json', feature.detailed_model_filename)

            # add any of the mapper measure variables
            if not @@mapper_measures.nil?
              @@mapper_measures.each do |map_measure_param|
                # get the attribute from the feature
                feature_param = feature.send(map_measure_param[2])
                # set the measure argument
                OpenStudio::Extension.set_measure_argument(
                  osw, map_measure_param[0], map_measure_param[1], feature_param)
              end
            end

            # add the feature id and name to the reporting measure
            OpenStudio::Extension.set_measure_argument(
              osw, 'default_feature_reports', 'feature_id', feature_id)
            OpenStudio::Extension.set_measure_argument(
              osw, 'default_feature_reports', 'feature_name', feature_name)
            OpenStudio::Extension.set_measure_argument(
              osw, 'default_feature_reports', 'feature_type', feature_type)
            OpenStudio::Extension.set_measure_argument(
              osw, 'default_feature_reports', 'feature_location', feature_location)

        end
        return osw
      end

    end #HoneybeeMapper
  end #Scenario
end #URBANopt