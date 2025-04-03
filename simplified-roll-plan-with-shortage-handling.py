import streamlit as st
import pandas as pd
import numpy as np
import random

# Title of the app
st.title("Simplified Roll Planning App")

# Create a file uploader widget
uploaded_file = st.file_uploader("Upload Cutplan Excel file", type=["xlsx"])

# Check if a file has been uploaded
if uploaded_file is not None:
    # Use Pandas to read the Excel file for each sheet
    with pd.ExcelFile(uploaded_file) as xls:
        # Assuming the names of the sheets are 'cutplan' and 'rolls_data'
        cutplan_df = pd.read_excel(xls, 'cutplan')
        rolls_df = pd.read_excel(xls, 'rolls_data')
    
    # Calculate total fabric uploaded and total fabric needed
    total_fabric_uploaded = round(rolls_df["Roll_Length"].sum(), 3)
    
    # Calculate total fabric needed directly from marker length and ply height
    total_fabric_needed = round(sum(cutplan_df["Marker_Length"] * cutplan_df["Ply_Height"]), 3)
    
    # Add 2% allowance to total fabric needed for warning calculation
    total_fabric_needed_with_allowance = total_fabric_needed * 1.02
    
    # Check for Bundles column
    if "Bundles" in cutplan_df.columns:
        # Calculate total number of garments
        total_garments = sum(cutplan_df["Bundles"] * cutplan_df["Ply_Height"])
    else:
        st.error("Error: Cutplan must contain a 'Bundles' column to calculate yield per garment.")
        st.stop()
    
    # Calculate Estimated Yield Per Garment
    estimated_yield_per_garment = round(total_fabric_needed / total_garments, 3)
    
    st.write(f"Estimated Yield Per Garment: {estimated_yield_per_garment}")
    
    # Display warning if fabric needed with allowance is more than uploaded
    if total_fabric_needed_with_allowance > total_fabric_uploaded:
        st.warning(f"""
        ⚠️ **WARNING: Insufficient Fabric Detected** ⚠️
        
        The total fabric needed ({total_fabric_needed} units) plus a 2% allowance ({total_fabric_needed_with_allowance:.3f} units) 
        exceeds the total fabric uploaded ({total_fabric_uploaded} units).
        
        Roll plans will likely result in incomplete plies and shortfall in garment production.
        """)
    
    # Run calculation button
    if st.button('Run 50 Random Roll Plans'):
        # Number of iterations
        num_iterations = 50
        
        # Find the longest marker length and smallest marker length
        longest_marker = cutplan_df["Marker_Length"].max()
        smallest_marker = cutplan_df["Marker_Length"].min()
        
        # Lists to track statistics across iterations with improved names
        excess_rolls_list = []
        fabric_saved_in_roll_form_list = []
        usable_end_bits_list = []
        unusable_bits_list = []
        
        # Lists to track ply shortfall statistics
        total_ply_shortfall_list = []
        shortfall_quantity_list = []  # Renamed from incomplete_bundles_list
        garments_produced_list = []   # New metric to track garments actually produced
        
        # Lists to track end bits grouping across iterations
        max_bundles = int(longest_marker / estimated_yield_per_garment)
        end_bits_group_counts_list = [[] for _ in range(max_bundles)]
        end_bits_group_sums_list = [[] for _ in range(max_bundles)]
        
        # Status indicator
        status_text = st.empty()
        
        # Run the specified number of iterations
        for iteration in range(num_iterations):
            status_text.text(f"Running iteration {iteration+1}/{num_iterations}")
            
            # Create a copy of the rolls data to work with and round the lengths
            available_rolls = [(roll_num, round(roll_length, 3)) 
                              for roll_num, roll_length in zip(rolls_df['Roll_Number'], 
                                                              rolls_df['Roll_Length'])]
            
            # Initialize tracking variables
            end_bits = []  # Keep track of all end bits/residuals
            total_ply_shortfall = 0  # Track total ply shortfall for this iteration
            shortfall_quantity = 0   # Track shortfall quantity (renamed from incomplete_bundles)
            garments_produced = 0    # Track total garments produced in this iteration
            
            # Separate normal rolls from residual rolls
            regular_rolls = [roll for roll in available_rolls]
            residual_rolls = []  # Start with no residuals
            
            # Process each marker in the cutplan
            for marker_name, marker_length, ply_height, bundles in zip(
                cutplan_df["Marker_Name"], 
                cutplan_df["Marker_Length"], 
                cutplan_df["Ply_Height"],
                cutplan_df["Bundles"]):
                
                selected_rolls = []
                plies_planned = 0
                marker_residuals = []
                
                # IMPORTANT CHECK: Check if any roll is long enough for at least one ply
                can_make_at_least_one_ply = False
                for roll in regular_rolls + residual_rolls:
                    if roll[1] >= marker_length:
                        can_make_at_least_one_ply = True
                        break
                
                # If no roll is long enough, skip to the next marker after recording shortfall
                if not can_make_at_least_one_ply:
                    ply_shortfall = ply_height
                    total_ply_shortfall += ply_shortfall
                    current_shortfall = ply_shortfall * bundles
                    shortfall_quantity += current_shortfall
                    continue  # Skip to the next marker
                
                # First, find the longest residual roll that's usable (if any)
                usable_residuals = [roll for roll in residual_rolls if roll[1] >= marker_length]
                
                # Use only the single longest residual roll first (if available)
                if usable_residuals:
                    # Sort to find the longest residual
                    usable_residuals.sort(key=lambda x: x[1], reverse=True)
                    roll = usable_residuals[0]
                    residual_rolls.remove(roll)
                    
                    roll_name, roll_length = roll
                    
                    # Calculate how many full plies we can get from this roll
                    plies_from_roll = min(int(roll_length // marker_length), ply_height - plies_planned)
                    
                    if plies_from_roll > 0:
                        # We can use this roll
                        plies_planned += plies_from_roll
                        fabric_used = plies_from_roll * marker_length
                        
                        # Calculate residual length
                        residual_length = round(roll_length - fabric_used, 3)
                        
                        # Add to selected rolls
                        selected_rolls.append((roll_name, roll_length))
                        
                        # Track residual if it exists
                        if residual_length > 0:
                            residual_name = f"{roll_name}-bit"
                            marker_residuals.append((residual_name, residual_length))
                    else:
                        # Roll is too short for this marker - instead of adding back, 
                        # move to unused with other rolls that are too short
                        end_bits.append((roll_name, roll_length))
                
                # If we still need more fabric, prioritize regular rolls over remaining residuals
                if plies_planned < ply_height:
                    # Shuffle regular rolls for randomness
                    random.shuffle(regular_rolls)
                    
                    # NEW APPROACH: Create a temporary list for rolls too short for this marker
                    too_short_rolls = []
                    
                    # Continue selecting rolls until we have enough fabric or run out of regular rolls
                    while plies_planned < ply_height and regular_rolls:
                        # Take the next roll
                        roll = regular_rolls.pop(0)
                        roll_name, roll_length = roll
                        
                        # Calculate how many full plies we can get from this roll
                        plies_from_roll = min(int(roll_length // marker_length), ply_height - plies_planned)
                        
                        if plies_from_roll > 0:
                            # We can use this roll
                            plies_planned += plies_from_roll
                            fabric_used = plies_from_roll * marker_length
                            
                            # Calculate residual length
                            residual_length = round(roll_length - fabric_used, 3)
                            
                            # Add to selected rolls
                            selected_rolls.append((roll_name, roll_length))
                            
                            # Track residual if it exists
                            if residual_length > 0:
                                residual_name = f"{roll_name}-bit"
                                marker_residuals.append((residual_name, residual_length))
                        else:
                            # Roll is too short for this marker - add to temporary list
                            too_short_rolls.append(roll)
                    
                    # Add the too-short rolls back to regular_rolls after processing
                    regular_rolls.extend(too_short_rolls)
                
                # After using all regular rolls, if we still need more, use remaining residuals
                if plies_planned < ply_height and residual_rolls:
                    # Sort residuals by length (longest first)
                    residual_rolls.sort(key=lambda x: x[1], reverse=True)
                    
                    # NEW APPROACH: Create a temporary list for residuals too short for this marker
                    too_short_residuals = []
                    
                    while plies_planned < ply_height and residual_rolls:
                        # Take the longest residual
                        roll = residual_rolls.pop(0)
                        roll_name, roll_length = roll
                        
                        # Calculate how many full plies we can get from this roll
                        plies_from_roll = min(int(roll_length // marker_length), ply_height - plies_planned)
                        
                        if plies_from_roll > 0:
                            # We can use this roll
                            plies_planned += plies_from_roll
                            fabric_used = plies_from_roll * marker_length
                            
                            # Calculate residual length
                            residual_length = round(roll_length - fabric_used, 3)
                            
                            # Add to selected rolls
                            selected_rolls.append((roll_name, roll_length))
                            
                            # Track residual if it exists
                            if residual_length > 0:
                                residual_name = f"{roll_name}-bit"
                                marker_residuals.append((residual_name, residual_length))
                        else:
                            # Residual is too short for this marker - add to temporary list
                            too_short_residuals.append(roll)
                    
                    # Add the too-short residuals back to residual_rolls after processing
                    residual_rolls.extend(too_short_residuals)
                
                # Calculate garments produced and shortfall for this marker
                garments_produced_marker = plies_planned * bundles
                garments_produced += garments_produced_marker
                
                # RECORD SHORTFALL if plies_planned < ply_height
                if plies_planned < ply_height:
                    # Calculate shortfall
                    ply_shortfall = ply_height - plies_planned
                    total_ply_shortfall += ply_shortfall
                    
                    # Calculate shortfall quantity
                    current_shortfall = ply_shortfall * bundles
                    shortfall_quantity += current_shortfall
                
                # Add all marker residuals to the end_bits tracking list
                end_bits.extend(marker_residuals)
                
                # Check residuals to see if any can be reused for other markers
                for residual in marker_residuals:
                    residual_name, residual_length = residual
                    
                    # Add residual back to available residual rolls ONLY if it's longer than the smallest marker
                    if residual_length >= smallest_marker:
                        residual_rolls.append((residual_name, residual_length))
            
            # Handle unused rolls for this iteration
            unused_rolls = regular_rolls + residual_rolls
            
            # Also add any residuals that weren't added to residual_rolls because they were too small
            for marker_residual in end_bits:
                residual_name, residual_length = marker_residual
                # Only add small residuals that were never reused
                if residual_length < smallest_marker and (residual_name, residual_length) not in unused_rolls:
                    unused_rolls.append((residual_name, residual_length))
            
            # Calculate statistics for unused original rolls only (not residual bits)
            excess_rolls = [roll for roll in unused_rolls 
                           if not (isinstance(roll[0], str) and "-bit" in roll[0])]
            excess_rolls_sum = round(sum(length for _, length in excess_rolls), 3)
            
            # Calculate different categories of leftover fabric based on Estimated Yield Per Garment
            fabric_saved_in_roll_form = [roll for roll in unused_rolls if roll[1] >= longest_marker]
            usable_end_bits = [roll for roll in unused_rolls 
                             if roll[1] < longest_marker and roll[1] >= estimated_yield_per_garment]
            unusable_bits = [roll for roll in unused_rolls if roll[1] < estimated_yield_per_garment]
            
            # Group usable end bits by multiples of yield per garment
            # First, find the maximum number of bundles possible
            max_bundles = int(longest_marker / estimated_yield_per_garment)
            
            # Initialize grouping lists for each iteration
            end_bits_groups = []
            for i in range(max_bundles):
                end_bits_groups.append([])
            
            # Categorize each end bit into appropriate group
            for roll in usable_end_bits:
                roll_name, roll_length = roll
                for i in range(max_bundles):
                    lower_bound = (i + 1) * estimated_yield_per_garment
                    upper_bound = (i + 2) * estimated_yield_per_garment if i < max_bundles - 1 else float('inf')
                    
                    if lower_bound <= roll_length < upper_bound:
                        end_bits_groups[i].append(roll)
                        break
            
            # Calculate counts and sums for each group
            end_bits_group_counts = [len(group) for group in end_bits_groups]
            end_bits_group_sums = [round(sum(length for _, length in group), 3) for group in end_bits_groups]
            
            # Sum up fabric amounts for each category
            fabric_saved_in_roll_form_sum = round(sum(length for _, length in fabric_saved_in_roll_form), 3)
            usable_end_bits_sum = round(sum(length for _, length in usable_end_bits), 3)
            unusable_bits_sum = round(sum(length for _, length in unusable_bits), 3)
            
            # Store statistics for this iteration
            excess_rolls_list.append(excess_rolls_sum)
            fabric_saved_in_roll_form_list.append(fabric_saved_in_roll_form_sum)
            usable_end_bits_list.append(usable_end_bits_sum)
            unusable_bits_list.append(unusable_bits_sum)
            total_ply_shortfall_list.append(total_ply_shortfall)
            shortfall_quantity_list.append(shortfall_quantity)
            garments_produced_list.append(garments_produced)
            
            # Store end bits grouping statistics
            for i in range(max_bundles):
                end_bits_group_counts_list[i].append(end_bits_group_counts[i])
                end_bits_group_sums_list[i].append(end_bits_group_sums[i])
        
        # Clear status indicator
        status_text.empty()
        
        # Calculate average statistics
        avg_excess_rolls = round(sum(excess_rolls_list) / num_iterations, 3)
        avg_fabric_saved_in_roll_form = round(sum(fabric_saved_in_roll_form_list) / num_iterations, 3)
        avg_usable_end_bits = round(sum(usable_end_bits_list) / num_iterations, 3)
        avg_unusable_fabric = round(sum(unusable_bits_list) / num_iterations, 3)
        avg_ply_shortfall = round(sum(total_ply_shortfall_list) / num_iterations, 1)
        avg_shortfall_quantity = round(sum(shortfall_quantity_list) / num_iterations, 1)
        avg_garments_produced = round(sum(garments_produced_list) / num_iterations, 1)
        
        # Calculate average end bits grouping statistics
        avg_end_bits_group_counts = []
        avg_end_bits_group_sums = []
        for i in range(max_bundles):
            avg_count = round(sum(end_bits_group_counts_list[i]) / num_iterations, 3)
            avg_sum = round(sum(end_bits_group_sums_list[i]) / num_iterations, 3)
            avg_end_bits_group_counts.append(avg_count)
            avg_end_bits_group_sums.append(avg_sum)
        
        # Calculate percentages
        total_wastage = avg_usable_end_bits + avg_unusable_fabric
        wastage_percentage = round((total_wastage / total_fabric_needed) * 100, 3)
        usable_end_bits_percentage = round((avg_usable_end_bits / total_fabric_needed) * 100, 3)
        ply_shortfall_percentage = round((avg_ply_shortfall / sum(cutplan_df["Ply_Height"])) * 100, 1)
        shortfall_percentage = round((avg_shortfall_quantity / total_garments) * 100, 1)
        garments_produced_percentage = round((avg_garments_produced / total_garments) * 100, 1)
        
        # Display the summary statistics
        st.header("Summary Statistics (Averages Across 50 Iterations)")
        st.write(f"Total Fabric Uploaded: {total_fabric_uploaded}")
        st.write(f"Total Fabric Needed in Marker: {total_fabric_needed}")
        st.write(f"Total Number of Garments: {total_garments}")
        st.write(f"Estimated Yield Per Garment: {estimated_yield_per_garment}")
        
        # Create two columns for better layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Fabric Utilization")
            st.write(f"Average Fabric in Excess Rolls: {avg_excess_rolls}")
            st.write(f"Average Fabric Saved in Roll Form: {avg_fabric_saved_in_roll_form}")
            st.write(f"Average Usable End Bits: {avg_usable_end_bits}")
            st.write(f"Average Usable End Bits %: {usable_end_bits_percentage}%")
            st.write(f"Average Unusable Fabric: {avg_unusable_fabric}")
            st.write(f"Total Wastage %: {wastage_percentage}%")
        
        with col2:
            st.subheader("Production Shortfall")
            st.write(f"Average Ply Shortfall: {avg_ply_shortfall}")
            st.write(f"Ply Shortfall %: {ply_shortfall_percentage}%")
            st.write(f"Average Shortfall Quantity: {avg_shortfall_quantity}")
            st.write(f"Shortfall Quantity %: {shortfall_percentage}%")
            st.write(f"Average Garments Cut: {avg_garments_produced}")
            st.write(f"Garments Cut vs Total: {garments_produced_percentage}%")
        
        # Display usable end bits grouping in a tabular format
        st.header("Usable End Bits Grouping")
        
        # Create data for the table
        table_data = []
        for i in range(max_bundles):
            lower_bound = i + 1
            upper_bound = i + 2
            table_data.append({
                "Group": f"End Bits for {lower_bound}-{upper_bound} bundles",
                "Avg. Number of End Bits": int(avg_end_bits_group_counts[i]),  # Floor the value
                "Avg. Fabric Available in Group": avg_end_bits_group_sums[i]
            })
        
        # Create the DataFrame and display it
        end_bits_table = pd.DataFrame(table_data)
        st.table(end_bits_table)