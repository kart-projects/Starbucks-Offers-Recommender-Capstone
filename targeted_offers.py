# Import required libraries
import sys
import pandas as pd
import numpy as np
import math
import json

def load_data(portfolio_filepath, transcript_filepath, profile_filepath):
    """
    (1) Load portfolio json file into Pandas dataframe called portfolio
    (2) Load transcript json file into Pandas dataframe called transcript
    (3) Load profile json file into Pandas dataframe called profile

     Parameters
     ----------
     portfolio_filepath : portfolio.json filepath
     transcript_filepath : transcript.json filepath
     profile_filepath : profile.json filepath

     Returns
     -------
     portfolio : The portfolio dataframe
     transcript : The transcript dataframe
     profile : The profile dataframe

     """
    # Read the portfolio json dataset into pandas dataframe portfolio
    portfolio = pd.read_json('data/portfolio.json', orient='records', lines=True)

    # Read the transcript json dataset into pandas dataframe transcript
    transcript = pd.read_json('data/transcript.json', orient='records', lines=True)
	
	# Read the profile json dataset into pandas dataframe profile
    profile = pd.read_json('data/profile.json', orient='records', lines=True)

    # Return the dataframes for further cleaning
    return portfolio, transcript, profile 

def clean_data(profile):
    """
     (1) Clean the profile dataframe to remove all invalid records.
     (2) Look for None values in "gender" column and removes these records.
     (3) Look for age = 118 and remove these records.
     (4) Drop records with NaN value in any column.

     Parameters
     ----------
     profile : The profile dataframe to clean for invalid values.
     
     Returns
     -------
     df : The dataframe that is clean and ready to for analysis.

     """
    # Drop any invalid values in the gender column (e.g. drop rows with None in gender)
    df = profile.dropna(subset=['gender'])

    # Drop rows with age = 118
    df = df[df['age'] != 118]
    
    # Drop all other rows with invalid values in any field (i.e. say if a row has NaN in income column, then drop it)
    df = df.dropna(how="all")
    
    # Return the dataframe for modeling and analysis
    return df
	
def subset_profile(profile, ruleId, age_25thperc, median_income):
    """
    Subset the profile data to return rows containing female customers >= 45 years and earning >=64K 

     Parameters
     ----------
     profile : The profile dataframe to subset.
     
     Returns
     -------
     df : The dataframe with required cases ready to for analysis.

    """
    if ruleId == 1:
        # Subset the profile data to return rows containing female customers >= 45 years and earning >=64K 
        df = profile[(profile.gender == "F") & (profile.age >= age_25thperc) & (profile.income >= median_income)]
    elif ruleId == 2:
        # Subset the profile data to return rows containing male customers < 45 years and earning <64K
        df = profile[(profile.gender == "M") & (profile.age < age_25thperc) & (profile.income < median_income)]
    else:
        # Subset the profile data to return rows containing male customers with age >= 45 years and earning >=64K 
        df = profile[(profile.gender == "M") & (profile.age >= age_25thperc) & (profile.income >= median_income)]
    # Return the dataframe for modeling and analysis
    return df
	
def has_customer_trasacted(customerId, transacted_customers):
    """
    Create has_transacted column to profile
    
    Parameters
    ----------
    customerId: Customer Id.
    
	transacted_customers : List of customers with one or more transactions.
     
    Returns
    -------
    boolean value if the customer with the given customer Id had transacted using the mobile app 
    """
    return customerId in transacted_customers

def has_transacted(transcript, profile):
    """
    Create has_transacted column to profile
    
    Parameters
    ----------
    transcript: The transcript dataframe containing the events from the mobile app for all customers.
    
	profile : The profile dataframe to append has_transacted column.
     
    Returns
    -------
    None 
    """
    
	# Create the transactions dataframe with only all user transactions i.e. with "transaction" event
    transactions = transcript[transcript.event == "transaction"]
	
    # Create transacted_customers, a vector with all unique users who were involved in a transaction i.e. with "transaction" event
    transacted_customers = transactions.person.unique()
	
    profile["has_transacted"] = profile.apply(lambda x: has_customer_trasacted(x.id, transacted_customers),axis=1)
	

def get_customer_events(customerId, transcript):
    """
    Get all the customer event rows from transcript dataframe
    
    Parameters
    ----------
    customerId: Customer Id.
    
	transcript : The transcript dataframe containing events of all customers
     
    Returns
    -------
    A dataframe with only rows for customer Id
    """
    return transcript[transcript.person == customerId] 
	
def influencing_offers(customerId, transcript):
    """
    Create a list of all Influencing offers for the passed customer Id and append.
    Influencing offers are found by looking at the completed offers and also making sure the customer viewed the offer before they completed the offer based on the key offer_id in the transcript dataframe.
    
    Parameters
    ----------
    customerId: Customer Id.
    
	transcript : The transcript dataframe containing events of all customers
     
    Returns
    -------
    A dataframe with only rows for customer Id
    """
    # Subset all events in the transcript dataframe for a given customerId
    df_customer_events = get_customer_events(customerId, transcript)
    # Subset all offer completed events in df_customer_events dataframe
    df_customer_events_completed_offers = df_customer_events[df_customer_events.event == "offer completed"]
    # Subset all offer viewed events in df_customer_events dataframe
    df_customer_events_viewed_offers = df_customer_events[df_customer_events.event == "offer viewed"]
    # Accumulate only the offers that have influenced customer transaction by checking if an offer was viewed -
	# by the customer before completing it.
    offers = []
    for i1, v1 in df_customer_events_completed_offers.iterrows():
        for i2, v2 in df_customer_events_viewed_offers.iterrows():
            if(v1['value']['offer_id'] == v2['value']['offer id'] and v2['time'] <= v1['time']):
                offers.append(v1['value']['offer_id'])
    # Return the influencing offers list for the queried customer.
    return offers
	
def offer_in_influencing_offers(offerId, influencing_offers):
    """
    Find if a passed offerId is in the influencing_offers list
    
    Parameters
    ----------
    offerId: Offer Id from portfolio dataframe.
    
	influencing_offers : List of offers found for a customer
     
    Returns
    -------
    1 if offer is found 0 if not found
    """
    if (offerId in influencing_offers):
        return 1
    else:
        return 0

def targeted_offers(profile_active, transcript, portfolio, ruleId):
    """
    (1) Create subset of population to analyze based on the ruleId
    (2) Find influencing offers for the targeted i.e. subset profile created in (1)
    (3) Find the top two influencing offers based on majority vote approach for this targeted poulation.
    (4) Recommend the two influencing offers for other customers in this population who have either not transacted or do not have any influening offers.
	
    Parameters
    ----------
    profile_active: All active customer profiles.
    
    transcript: The transcript dataframe containing the events from the mobile app for all customers.
	
    portfolio: The portfolio datframe containing all offer details including offer Id, offer type and reward information.
    
	ruleId : rule to apply to create subet of targetted population. 
	         1 = Female population with age >= 45 and salary >= 65K
             2 = Male population with age >= 45 and salary >= 65K     
			 
    Returns
    -------
    None
    """
    # Male population 
    pop_type = "male"
    # Age >= 45
    age_group = ">= 45"
    # Salary >= 64000
    salary_limit = ">= 64000"
    # If the ruleId is 1 then swap the population type to female with age >= 45 
    if ruleId == 1:
        pop_type = "female"
        age_group = ">= 45"
    elif ruleId == 2:
        pop_type = "male"
        age_group = "< 45"
        salary_limit = "< 64000"
    # Subset based on ruleID		
    print("\n    Subset profile data to include cases with {} customers with age {} and income {}".format(pop_type, age_group,salary_limit))
        
    profile_active_45_64K = subset_profile(profile_active, ruleId=ruleId, age_25thperc=45, median_income=64000)
              
    print("\n\n    PROFILE_ACTIVE_45_64K: Rows = {0}, Columns = {1}".format(str(profile_active_45_64K.shape[0]), str(profile_active_45_64K.shape[1])))
        
    print(profile_active_45_64K.head())

    # Add has_transacted colum to the profile_active_45_64K dataframe 	
    print("\n\n    Create a new column has_transacted in PROFILE_ACTIVE_45_64K dataframe containing boolean values showing if a customer has transacted using the mobile app or not.\n")
		
    has_transacted(transcript, profile_active_45_64K)

    print(profile_active_45_64K.head())
		
    # Subset transacted and not transacted customers and report the counts
    profile_active_45_64K_transacted = profile_active_45_64K[profile_active_45_64K.has_transacted]
		
    print("\n\n    PROFILE_ACTIVE_45_64K_TRANSACTED: Rows = {0}, Columns = {1}".format(str(profile_active_45_64K_transacted.shape[0]), str(profile_active_45_64K_transacted.shape[1])))
        
    profile_active_45_64K_not_transacted = profile_active_45_64K[profile_active_45_64K.has_transacted == False]
		
    print("\n\n    PROFILE_ACTIVE_45_64K_NOT_TRANSACTED: Rows = {0}, Columns = {1}".format(str(profile_active_45_64K_not_transacted.shape[0]), str(profile_active_45_64K_not_transacted.shape[1])))

    # Search for influencing offers for transacted customers
    print("\n\n    Searching for influencing offers using the \"transcript\" dataframe for {} {} customers with age {} years and annual income {}...Please wait...might take about 2-4 minutes on machines with average computing power...".format(str(profile_active_45_64K_transacted.shape[0]), pop_type, age_group, salary_limit))
		
    profile_active_45_64K_transacted["influencing_offers"] = profile_active_45_64K_transacted.apply(lambda x:influencing_offers(x.id, transcript),axis=1)
		
    # Drop all the rows with empty influencing offers for transacted customers
    profile_active_45_64K_transacted = profile_active_45_64K_transacted[profile_active_45_64K_transacted.influencing_offers.str.len()!=0]
		
    print("\n\n    PROFILE_ACTIVE_45_64K_NOT_TRANSACTED after dropping customers with no influencing offers: Rows = {0}, Columns = {1}".format(str(profile_active_45_64K_not_transacted.shape[0]), str(profile_active_45_64K_not_transacted.shape[1])))
    
    # Report the final dataframe head() rows    
    print(profile_active_45_64K_transacted.head())
     
    # Count all influencing offers for this population	 
    offer_counts = []
    i = 0
    for offerId in portfolio.id:
        profile_active_45_64K_transacted[offerId] = profile_active_45_64K_transacted.apply(lambda x:offer_in_influencing_offers(offerId, x.influencing_offers), axis=1)
        offer_counts.append(np.sum(profile_active_45_64K_transacted[offerId]))
        print(str(offerId) + " - " + str(offer_counts[i]))
        i = i + 1
    # Find maximum influencing offer based on majority vote i.e. by counting all influenced customers
    index_of_max_influencing_offer = offer_counts.index(max(offer_counts)) 
    
    # Report the maximum influencing offer for this population
    print("\n\nThe maximum influencing offer for {} population with age {} years and annual income {},\n {} - {} \n with count - {}\n influencing {} {}.".format(pop_type, age_group, salary_limit, str(portfolio.id.iloc[index_of_max_influencing_offer]), str(portfolio.offer_type.iloc[index_of_max_influencing_offer]), str(offer_counts[index_of_max_influencing_offer]), str(profile_active_45_64K_transacted.shape[0]), pop_type))
    
    # Find the secomd maximum influencing offer for this population	
    second_max_offer = 0
    i = 0
    index_of_second_max_offer = -1
    for cnt in offer_counts:
        if cnt > second_max_offer and i!=index_of_max_influencing_offer:
            second_max_offer = cnt
            index_of_second_max_offer = i
        i = i + 1
		
    # Find the index of the next most influencing offer in the offer list
    index_of_max_influencing_offer = offer_counts.index(max(offer_counts))
	
    # Report the second maximum influencing offer	
    print("\n\nThe second maximum influencing offer for {} population with age {} years and annual income {},\n {} - {} \n with count - {}\n influencing {} {}.".format(pop_type, age_group, salary_limit, str(portfolio.id.iloc[index_of_second_max_offer]), str(portfolio.offer_type.iloc[index_of_second_max_offer]), str(offer_counts[index_of_second_max_offer]), str(profile_active_45_64K_transacted.shape[0]),pop_type))
        
    # Summarize our findings and recommendations based on the above analysis
    print("\n\nLooks like this population of {} customers loves discounts.\nWe should surely recommend these offers for other {} customers in the same population who have either not transacted at all with the mobile app or were not previously influenced by this offer".format(pop_type, pop_type))
		
def main():
    """
    The main execution function that takes in the user provided terminal arguments
    and runs the built functions to perform Extract, Tranform and Load (ETL) tasks:

    (1) load_data(...) - Load the json files into their respective dataframes
    (2) clean_data(...) - Remove any invalid data from profile dataframe
    (3) targeted_offers(...) - Subset the profile data to include only the rows to analyze
        (i) Create subset of population to analyze based on the ruleId
        (ii) Find influencing offers for the targeted i.e. subset profile created in (1)
        (iii) Find the top two influencing offers based on majority vote approach for this targeted poulation.
        (iv) Recommend the two influencing offers for other customers in this population who have either not transacted or do not have any influening offers.
    (4) Handle command line errors

    Parameters
    ----------
    None

    Returns
    -------
    None

    """
    if len(sys.argv) == 4:

        portfolio_filepath, transcript_filepath, profile_filepath = sys.argv[1:]

        print('Loading data...\n    PORTFOLIO: {}\n    TRANSCRIPT: {}\n    PROFILE: {}'
              .format(portfolio_filepath, transcript_filepath, profile_filepath))

        portfolio, transcript, profile = load_data(portfolio_filepath, transcript_filepath, profile_filepath)

        print("\n\n    PORTFOLIO: Rows = {0}, Columns = {1}".format(str(portfolio.shape[0]), str(portfolio.shape[1])))
        print("\n\n    TRANSCRIPT: Rows = {0}, Columns = {1}".format(str(transcript.shape[0]), str(transcript.shape[1])))
        print("\n\n    PROFILE: Rows = {0}, Columns = {1}".format(str(profile.shape[0]), str(profile.shape[1])))
        
        print(profile.head())

        print('Cleaning profile data...')
        profile_active = clean_data(profile)
        
        print("\n\n    PROFILE_ACTIVE: Rows = {0}, Columns = {1}".format(str(profile_active.shape[0]), str(profile_active.shape[1])))
        
        print(profile_active.head())

        # Analyze offers for female customers >= 45 years and earning >= 64K      
        targeted_offers(profile_active, transcript, portfolio, ruleId=1)
        print("________________________________________________________________________________________________________________")

        # Analyze offers for male customers < 45 years and earning < 64K         
        targeted_offers(profile_active, transcript, portfolio, ruleId=2)
        print("________________________________________________________________________________________________________________")
		
        # Analyze offers for male customers >= 45 years and earning >= 64K      
        targeted_offers(profile_active, transcript, portfolio, ruleId=3)
        print("________________________________________________________________________________________________________________")
		
        print('\n\nSearch for influencing offers was completed successfully! Thanks for using this program.')

    else:
        print('Please provide the filepaths of the portfolio, profile and transcript '\
              'datasets as the first, second and third argument respectively.'\
              '\n\nExample: python targeted_offers.py '\
              'portfolio.json transcript.json profile.json')

# Invoke the main function
if __name__ == '__main__':
    main()
